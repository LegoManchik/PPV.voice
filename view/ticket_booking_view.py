import random
from typing import Optional

import discord.ui
from discord import TextChannel, TextStyle
from discord.utils import get

from discord.ext import commands

import config

from database.database import TicketBookingDatabase
from utils.seat_data import SeatData
from utils.localization import Localization

FLOOR_1_EMBED = discord.Embed()
FLOOR_1_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827898085834812/Frame_15620.png")

FLOOR_2_EMBED = discord.Embed()
FLOOR_2_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827896471158896/Frame_15621.png")

FLOOR_3_EMBED = discord.Embed()
FLOOR_3_EMBED.set_image(url="https://media.discordapp.net/attachments/1365977478157303839/1366827894642573404/Frame_15623.png")

IMAGE_EMBED = discord.Embed()
IMAGE_EMBED.set_image(url="https://cdn.discordapp.com/attachments/1365977478157303839/1366495851408785438/image.png")

RENTAL_REQUEST_EMBED = discord.Embed(title="Новая заявка", description="{0} подал заяву на покупку билета")

SEAT_RESERVED_EMBED = discord.Embed(color=discord.Color.green())
APPLICATION_REJECTED_EMBED = discord.Embed(color=discord.Color.red())


class BookingTicketButton(discord.ui.View):
    def __init__(self, ctx: commands.Context, lang: str):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang

        button = discord.ui.Button(label=Localization.translatable("button.buy_ticket", lang), style=discord.ButtonStyle.red, custom_id='by_ticket_ru', row=1)
        button.callback = self.booking_ticket

        self.add_item(button)

    async def booking_ticket(self, interaction: discord.Interaction):
        guild = interaction.message.guild
        category = get(guild.categories, name="Tickets")
        random_int = random.randint(100, 999)

        await guild.create_text_channel(f'ticket-{self.lang}-{interaction.user.name}-{random_int}', category=category)

        everyone = guild.get_role(config.GUILD_ID)

        channel: TextChannel = get(category.channels, name=f'ticket-{self.lang}-{interaction.user.name}-{random_int}')

        await channel.set_permissions(interaction.user, read_messages=True, send_messages=False)
        await channel.set_permissions(get(guild.roles, id=config.SUPERVISOR_ROLE_ID), read_messages=True, send_messages=True)
        await channel.set_permissions(everyone, read_messages=False, send_messages=False)

        await channel.send(embed=IMAGE_EMBED, view=FloorsButtons(ctx=self.ctx, lang=self.lang))


#region Выбор этажа
class FloorsButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, lang: str):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang

    @discord.ui.button(emoji="1️⃣", style=discord.ButtonStyle.gray, custom_id='floor_1', row=1)
    async def floor_1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_1_EMBED, f"embed.floor_1", self.lang), view=ChoiceSeatButtons(self.ctx, 1, lang=self.lang))

    @discord.ui.button(emoji="2️⃣", style=discord.ButtonStyle.gray, custom_id='floor_2', row=1)
    async def floor_2_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_2_EMBED, f"embed.floor_2", self.lang), view=ChoiceSeatButtons(self.ctx, 2, lang=self.lang))

    @discord.ui.button(emoji="3️⃣", style=discord.ButtonStyle.gray, custom_id='floor_3', row=1)
    async def floor_3_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=Localization.translatable_embed(FLOOR_3_EMBED, f"embed.floor_3", self.lang), view=ChoiceSeatButtons(self.ctx, 3, lang=self.lang))
# endregion


# region Выбор места на этаже
class ChoiceSeatButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, floor: int, lang: str):
        super().__init__(timeout=None)
        self.db = TicketBookingDatabase()

        self.ctx = ctx
        self.floor = floor
        self.lang = lang

        for seat, user_id in self.db.get_seat_list(floor):
            button = discord.ui.Button(label=str(seat), style=discord.ButtonStyle.gray, custom_id=seat, disabled=user_id is not None)
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
            description=data.get_description(lang=self.lang)
        )
        embed.set_image(url=data.get_image())

        await interaction.response.edit_message(embed=embed, view=SeatButtons(ctx=self.ctx, floor=self.floor, seat=str(interaction.data.get("custom_id")), lang=self.lang))

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=IMAGE_EMBED, view=FloorsButtons(self.ctx, lang=self.lang))
# endregion


# region Кнопки выбранного места
class SeatButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, floor: int, seat: str, lang: str, disabled: bool = False):
        super().__init__(timeout=None)
        self.value: Optional[bool] = None
        self.ctx = ctx
        self.floor = floor
        self.seat = seat
        self.lang = lang

        back_button = discord.ui.Button(emoji="⬅", style=discord.ButtonStyle.gray, custom_id='seat_back', row=1, disabled=disabled)
        back_button.callback = self.back_callback

        rental_seat_button = discord.ui.Button(label=Localization.translatable("button.buy_ticket", lang), style=discord.ButtonStyle.green, custom_id=f'{seat}_rental', row=1, disabled=disabled)
        rental_seat_button.callback = self.rental_seat_callback

        self.add_item(back_button)
        self.add_item(rental_seat_button)

    async def back_callback(self, interaction: discord.Interaction):
        embed = {"1": FLOOR_1_EMBED, "2": FLOOR_2_EMBED, "3": FLOOR_3_EMBED}[str(self.floor)]
        await interaction.response.edit_message(embed=Localization.translatable_embed(embed, f"embed.floor_{self.floor}", self.lang),  view=ChoiceSeatButtons(self.ctx, floor=self.floor, lang=self.lang))

    async def rental_seat_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayersModal(ctx=self.ctx, floor=self.floor, seat=self.seat, lang=self.lang, message=interaction.message))
# endregion


# region Сообщение-заявка на покупку билета
class RentalRequestButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, lang: str, ticket_data: dict, disabled: bool = False):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx

        self.db = TicketBookingDatabase()
        self.ticket_data: dict = ticket_data

        self.channel: discord.TextChannel = ticket_data.get('channel')
        self.floor: str = ticket_data.get('floor')
        self.seat: str = ticket_data.get('seat')
        self.user: discord.User = ticket_data.get('user')
        self.players: str = ticket_data.get('players')

        self.lang: str = lang

        reject_button = discord.ui.Button(label="Отклонить", style=discord.ButtonStyle.red, custom_id='reject_seat', row=1, disabled=disabled)
        reject_button.callback = self.reject_callback

        approve_button = discord.ui.Button(label='Одобрить', style=discord.ButtonStyle.green, custom_id='approve_seat', row=1, disabled=disabled)
        approve_button.callback = self.approve_callback

        self.add_item(reject_button)
        self.add_item(approve_button)

    async def reject_callback(self, interaction: discord.Interaction):
        if get(interaction.user.roles, id=config.SUPERVISOR_ROLE_ID) is not None:

            await self.channel.delete(reason="Тикет отклонён")
            await interaction.response.edit_message(view=RentalRequestButtons(ctx=self.ctx, lang=self.lang, disabled=True, ticket_data=self.ticket_data))

            embed = Localization.translatable_embed(APPLICATION_REJECTED_EMBED, "embed.applivation_rejected", self.lang)
            embed.description = embed.description.format(self.seat)
            await self.user.send(embed=embed)

    async def approve_callback(self, interaction: discord.Interaction):
        if get(interaction.user.roles, id=config.SUPERVISOR_ROLE_ID) is not None:

            member = get(interaction.guild.members, name=self.channel.name.split('-')[2])
            await interaction.response.edit_message(
                view=RentalRequestButtons(ctx=self.ctx, lang=self.lang, disabled=True,
                                          ticket_data=self.ticket_data))

            self.db.add_user(int(self.floor), self.seat, self.user.id, self.players)

            await member.add_roles(get(interaction.guild.roles, id={"ru": config.RU_ROLE_ID, "en": config.EN_ROLE_ID}.get(str(interaction.message.embeds[0].footer.text.split('-')[1]))))

            await self.channel.send(self.user.mention, embed=Localization.translatable_embed(SEAT_RESERVED_EMBED, key="embed.seat_reserved", lang=self.lang))
            await self.channel.set_permissions(member, read_messages=True, send_messages=False)

# endregion


class AddPlayersModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label="modal_label.player_list",
        placeholder="modal_placeholder.prompt",
        custom_id=f"players_list",
        style=TextStyle.long,
        max_length=100
    )

    def __init__(self, *, title: str = "modal_title.player_list", timeout=None, custom_id: str = "add_players", ctx: commands.Context, floor: int, seat: str, lang: str, message):
        super().__init__(title=Localization.translatable(title, lang), timeout=timeout, custom_id=custom_id)

        self.players.label = Localization.translatable(self.players.label, lang)
        self.players.placeholder = Localization.translatable(self.players.placeholder, lang)

        self.ctx = ctx
        self.message = message
        self.floor = floor
        self.seat = seat
        self.lang = lang

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = get(guild.channels, id=config.CONFIRMATION_CHANNEL_ID)

        RENTAL_REQUEST_EMBED.description = RENTAL_REQUEST_EMBED.description.format(interaction.user.mention)
        RENTAL_REQUEST_EMBED.set_footer(text=f"#{interaction.channel.name}")
        RENTAL_REQUEST_EMBED.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
        RENTAL_REQUEST_EMBED.add_field(name="Приглашенные игроки:", value=f"```{self.players.value}```", inline=False)

        await self.message.edit(view=SeatButtons(ctx=self.ctx, floor=self.floor, seat=self.seat, lang=self.lang, disabled=True))
        await interaction.response.defer()

        ticket_data = {'channel': interaction.channel, 'floor': self.floor, 'seat': self.seat, 'user': interaction.user, 'players': self.players.value.split(' ')}

        await interaction.channel.set_permissions(get(interaction.guild.members, name=interaction.channel.name.split('-')[2]), read_messages=True, send_messages=True)
        await channel.send(content=f"<@&{config.SUPERVISOR_ROLE_ID}>", embed=RENTAL_REQUEST_EMBED, view=RentalRequestButtons(ctx=self.ctx, lang=self.lang, ticket_data=ticket_data))
