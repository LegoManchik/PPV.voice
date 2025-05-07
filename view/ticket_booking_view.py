from typing import Optional

import discord.ui
from discord import TextStyle
from discord.ext import commands
from discord.utils import get

import config

from data.database import TicketBookingDatabase, SeatStatus
from data.extract_json import JsonExtract
from data.seat_data import SeatData
from utils.localization import Localization, LangContext, Language
from utils.tickets import TicketSystem

FLOOR_1_EMBED = discord.Embed()
FLOOR_1_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827898085834812/Frame_15620.png")

FLOOR_2_EMBED = discord.Embed()
FLOOR_2_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827896471158896/Frame_15621.png")

FLOOR_3_EMBED = discord.Embed()
FLOOR_3_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827894642573404/Frame_15623.png")

IMAGE_EMBED = discord.Embed()
IMAGE_EMBED.set_image(url="https://cdn.discordapp.com/attachments/1365977478157303839/1366495851408785438/image.png")

SEAT_RESERVED_EMBED = discord.Embed(color=discord.Color.green())
APPLICATION_REJECTED_EMBED = discord.Embed(color=discord.Color.red())


class ConfirmationButton(discord.ui.View):
    def __init__(self, bot, lang: str):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.lang = lang
        self.bot = bot

        self.db = TicketBookingDatabase()

        button = discord.ui.Button(label=Localization.translatable("button.book_ticket", lang), style=discord.ButtonStyle.red, custom_id=f'book_ticket_{lang}', row=1)
        button.callback = self.confirm_callback

        self.add_item(button)

    async def confirm_callback(self, interaction: discord.Interaction):
        if not self.db.user_in_seats(interaction.user):
            ctx = await LangContext.get_context_from_interactionc(bot=self.bot, interaction=interaction)
            await interaction.response.send_message(embed=Localization.translatable_embed(discord.Embed(), key="embed.booking_confirm", lang=self.lang), view=BookingTicketButton(ctx=ctx, lang=self.lang), ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(
                embed=Localization.translatable_embed(discord.Embed(), key="embed.user_in_seat", lang=self.lang), ephemeral=True, delete_after=5)


class BookingTicketButton(discord.ui.View):
    def __init__(self, ctx: commands.Context, lang):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx: LangContext = LangContext(bot=ctx.bot, message=ctx.message, view=ctx.view)
        self.ctx.set_lang(lang=lang)
        self.ticket = TicketSystem(self.ctx.bot)

        button = discord.ui.Button(label=Localization.translatable("button.yes", self.ctx.lang), style=discord.ButtonStyle.green, custom_id=f'buy_ticket_{self.ctx.lang}', row=1)
        button.callback = self.booking_ticket

        self.add_item(button)

    async def booking_ticket(self, interaction: discord.Interaction):
        channel = await self.ticket.create_ticket(ctx=self.ctx, user=interaction.user, guild=interaction.message.guild)
        await channel.send(embed=Localization.translatable_embed(discord.Embed(), key="embed.floors", lang=self.ctx.lang), view=FloorsButtons(ctx=self.ctx))
        await interaction.response.send_message(channel.mention, ephemeral=True)


#region Выбор этажа
class FloorsButtons(discord.ui.View):
    def __init__(self, ctx: LangContext):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx

        self.ticket = TicketSystem(self.ctx.bot)

        floor_1 = discord.ui.Button(emoji="1️⃣", label="⠀⠀⠀⠀⠀⠀⠀⠀⠀", style=discord.ButtonStyle.gray, custom_id='floor_1', row=1)
        floor_2 = discord.ui.Button(emoji="2️⃣", label="⠀⠀⠀⠀⠀⠀⠀⠀⠀", style=discord.ButtonStyle.gray, custom_id='floor_2', row=1)
        floor_3 = discord.ui.Button(emoji="3️⃣", label="⠀⠀⠀⠀⠀⠀⠀⠀⠀", style=discord.ButtonStyle.gray, custom_id='floor_3', row=1)

        close_ticket = discord.ui.Button(label=f"{Localization.translatable('button.close_ticket', lang=self.ctx.lang):⠀^47}",
                                         style=discord.ButtonStyle.gray, custom_id='close_ticket', row=2)

        floor_1.callback = self.floor_1_callback
        floor_2.callback = self.floor_2_callback
        floor_3.callback = self.floor_3_callback

        close_ticket.callback = self.close_ticket_callback

        self.add_item(floor_1)
        self.add_item(floor_2)
        self.add_item(floor_3)
        self.add_item(close_ticket)

    async def floor_1_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_1_EMBED, f"embed.floor_1", self.ctx.lang), view=ChoiceSeatButtons(self.ctx, 1))

    async def floor_2_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_2_EMBED, f"embed.floor_2", self.ctx.lang), view=ChoiceSeatButtons(self.ctx, 2))

    async def floor_3_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_3_EMBED, f"embed.floor_3", self.ctx.lang), view=ChoiceSeatButtons(self.ctx, 3))

    async def close_ticket_callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await self.ticket.close_ticket(channel=channel)
        await channel.delete()

# endregion


# region Выбор места на этаже
class ChoiceSeatButtons(discord.ui.View):
    def __init__(self, ctx: LangContext, floor: int):
        super().__init__(timeout=None)
        self.db = TicketBookingDatabase()

        self.ctx = ctx
        self.floor = floor

        for seat, user_id, players, status in self.db.get_seat_list(floor):
            button = discord.ui.Button(label=str(seat), style=discord.ButtonStyle.gray, custom_id=seat, disabled=not self.db.is_avalible(floor, seat))
            button.callback = self.button_callback
            self.add_item(button)

        back_button = discord.ui.Button(emoji='⬅', style=discord.ButtonStyle.red, custom_id="back_to_floors", row=4)
        back_button.callback = self.back_callback
        self.add_item(back_button)

    async def button_callback(self, interaction: discord.Interaction):
        data = SeatData(floor=self.floor, seat=str(interaction.data.get("custom_id")))

        embed = discord.Embed(
            title=str(interaction.data.get("custom_id")),
            color=int(data.get_color(), 16),
            description=data.get_description(lang=self.ctx.lang)
        )
        embed.set_image(url=data.get_image())

        await interaction.response.edit_message(embed=embed, view=SeatButtons(ctx=self.ctx, floor=self.floor, seat=str(interaction.data.get("custom_id"))))

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=Localization.translatable_embed(discord.Embed(), key="embed.floors", lang=self.ctx.lang), view=FloorsButtons(self.ctx))
# endregion


# region Кнопки выбранного места
class SeatButtons(discord.ui.View):
    def __init__(self, ctx: LangContext, floor: int, seat: str, disabled: bool = False):
        super().__init__(timeout=None)
        self.value: Optional[bool] = None
        self.ctx = ctx
        self.floor = floor
        self.seat = seat

        back_button = discord.ui.Button(emoji="⬅", style=discord.ButtonStyle.gray, custom_id='seat_back', row=1, disabled=disabled)
        back_button.callback = self.back_callback

        rental_seat_button = discord.ui.Button(label=Localization.translatable("button.book_ticket", self.ctx.lang), style=discord.ButtonStyle.green, custom_id=f'{seat}_rental', row=1, disabled=disabled)
        rental_seat_button.callback = self.rental_seat_callback

        self.add_item(back_button)
        self.add_item(rental_seat_button)

    async def back_callback(self, interaction: discord.Interaction):
        embed = {"1": FLOOR_1_EMBED, "2": FLOOR_2_EMBED, "3": FLOOR_3_EMBED}[str(self.floor)]
        await interaction.response.edit_message(embed=Localization.translatable_embed(embed, f"embed.floor_{self.floor}", self.ctx.lang),  view=ChoiceSeatButtons(self.ctx, floor=self.floor))

    async def rental_seat_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayersModal(ctx=self.ctx, floor=self.floor, seat=self.seat, message=interaction.message))
# endregion


# region Сообщение-заявка на покупку билета
class RentalRequestButtons(discord.ui.View):
    def __init__(self, ctx: LangContext, ticket_data: dict, disabled: bool = False):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx

        self.db = TicketBookingDatabase()
        self.ticket = TicketSystem(bot=ctx.bot)
        self.ticket_data: dict = ticket_data

        self.channel: discord.TextChannel = ticket_data.get('channel')
        self.floor: str = ticket_data.get('floor')
        self.seat: str = ticket_data.get('seat')
        self.user: discord.User = ticket_data.get('user')
        self.players: str = ticket_data.get('players')

        reject_button = discord.ui.Button(label="Отклонить", style=discord.ButtonStyle.red, custom_id='reject_seat', row=1, disabled=disabled)
        reject_button.callback = self.reject_callback

        approve_button = discord.ui.Button(label='Одобрить', style=discord.ButtonStyle.green, custom_id='approve_seat', row=1, disabled=disabled)
        approve_button.callback = self.approve_callback

        self.add_item(reject_button)
        self.add_item(approve_button)

    async def reject_callback(self, interaction: discord.Interaction):
        if get(interaction.user.roles, id=config.SUPERVISOR_ROLE_ID) is not None or get(interaction.user.roles, id=config.OPERATOR_ROLE_ID) is not None:
            await self.ticket.close_ticket(self.channel)
            await self.channel.delete(reason="Тикет отклонён")

            self.db.set_seat_status(int(self.floor), self.seat, SeatStatus.AVAILABLE)

            interaction.message.embeds[0].set_footer(text="Статус: 💀")
            embed = interaction.message.embeds[0]

            await interaction.response.edit_message(embed=embed, view=RentalRequestButtons(ctx=self.ctx, disabled=True, ticket_data=self.ticket_data))

            embed = Localization.translatable_embed(APPLICATION_REJECTED_EMBED, "embed.applivation_rejected", self.ctx.lang)
            embed.description = embed.description.format(self.seat)
            await self.user.send(embed=embed)

    async def approve_callback(self, interaction: discord.Interaction):
        if get(interaction.user.roles, id=config.SUPERVISOR_ROLE_ID) is not None or get(interaction.user.roles, id=config.OPERATOR_ROLE_ID) is not None:

            member = get(interaction.guild.members, name=self.channel.name.split('-')[2])
            interaction.message.embeds[0].set_footer(text="Статус: ✅")
            embed = interaction.message.embeds[0]
            await interaction.response.edit_message(embed=embed, view=RentalRequestButtons(ctx=self.ctx, disabled=True, ticket_data=self.ticket_data))

            self.db.add_user(int(self.floor), self.seat, self.user.id, ' '.join(self.players))

            await member.add_roles(get(interaction.guild.roles, id=Language.lang_role_get(self.ctx.lang)))

            await self.channel.send(self.user.mention, embed=Localization.translatable_embed(SEAT_RESERVED_EMBED, key="embed.seat_reserved", lang=self.ctx.lang))
            await self.channel.set_permissions(member, read_messages=True, send_messages=False)
            await self.ticket.close_ticket(self.channel)

# endregion


class AddPlayersModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label="modal_label.player_list",
        placeholder="modal_placeholder.prompt",
        custom_id=f"players_list",
        style=TextStyle.long,
        max_length=100
    )

    def __init__(self, *, title: str = "modal_title.player_list", timeout=None, custom_id: str = "add_players", ctx: LangContext, floor: int, seat: str, message):
        super().__init__(title=Localization.translatable(title, ctx.lang), timeout=timeout, custom_id=custom_id)

        self.players.label = Localization.translatable(self.players.label, ctx.lang)
        self.players.placeholder = Localization.translatable(self.players.placeholder, ctx.lang)

        self.db = TicketBookingDatabase()

        self.ctx = ctx
        self.message = message
        self.floor = floor
        self.seat = seat

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = get(guild.channels, id=config.CONFIRMATION_CHANNEL_ID)

        self.db.set_seat_status(self.floor, self.seat, SeatStatus.UNAVAILABLE)

        embed = discord.Embed(title="Заявка", description=f"{interaction.user.mention} подал заяву на бронирования места **{self.seat}**")
        embed.set_author(name=interaction.channel.name, url=interaction.channel.jump_url, icon_url=interaction.user.avatar.url)
        embed.add_field(name="Приглашенные игроки:", value=f"```{self.players.value}```", inline=False)
        embed.set_footer(text="Статус: ❌")

        await self.message.edit(view=SeatButtons(ctx=self.ctx, floor=self.floor, seat=self.seat, disabled=True))
        await interaction.response.send_message(embed=Localization.translatable_embed(discord.Embed(), "embed.moderators_notification", lang=self.ctx.lang))

        ticket_data = {'channel': interaction.channel, 'floor': self.floor, 'seat': self.seat, 'user': interaction.user, 'players': self.players.value.split(' ')}

        await interaction.channel.set_permissions(get(interaction.guild.members, name=interaction.channel.name.split('-')[2]), read_messages=True, send_messages=True)
        await channel.send(content=f"<@{'> <@'.join(JsonExtract.get_user_id_list())}>", embed=embed, view=RentalRequestButtons(ctx=self.ctx, ticket_data=ticket_data))
