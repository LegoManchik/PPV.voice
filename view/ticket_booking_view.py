import logging
import traceback
from functools import wraps
from typing import Optional, Any

import discord

from discord import ui, MediaGalleryItem, Interaction, TextStyle

from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord.utils import get

import config
from data.enums import BookingStatus, SeatModes
from data.database import TicketBookingDatabase, SeatStatus
from data.json_helper import JsonHelper
from data.data_helper import SeatData, FloorData
from utils.decorators import is_moderator
from utils.localization import Localization, LangContext, Language
from utils.logger import BotLogger, interaction_error_handler
from utils.tickets import TicketSystem

SEAT_RESERVED_EMBED = discord.Embed(color=discord.Color.green())
APPLICATION_REJECTED_EMBED = discord.Embed(color=discord.Color.red())

logger = BotLogger().get_file_logger(__name__)


class BookingTicketButton(ui.Button):
    def __init__(self, ctx: Context, lang: str):
        self.ticket = TicketSystem(ctx.bot)

        super().__init__(label=Localization.translatable("button.yes", lang), style=discord.ButtonStyle.green, custom_id=f'buy_ticket_{lang}_{ctx.interaction.user.id}')

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        channel = await self.ticket.create_ticket(lang=self.lang, user=interaction.user, guild=interaction.message.guild)
        if JsonHelper.is_single_floor():
            floor = JsonHelper.get_floors()[0]

            if JsonHelper.is_single_seat(floor):
                seat_key = JsonHelper.get_single_seat_key(floor=floor)
                data = TicketBookingDatabase()
                seat = data.get_seat(floor=floor, seat=seat_key)

                await channel.send(view=SeatView(ctx=self.ctx, lang=self.lang, floor=floor, seat=seat_key))
            else:
                await channel.send(view=ChoiseSeatView(ctx=self.ctx, lang=self.lang, floor=floor))
        else:
            await channel.send(view=ChoiseFloorView(ctx=self.ctx, lang=self.lang))

        await interaction.response.send_message(channel.mention, ephemeral=True)


class StartBookingButton(ui.Button):
    def __init__(self, bot: Bot, lang: str):
        self.database = TicketBookingDatabase()

        super().__init__(label=Localization.translatable("button.book_ticket", lang), style=discord.ButtonStyle.red, custom_id=f'book_ticket_{lang}', row=1)

        self.value: Optional[bool] = None
        self.bot = bot
        self.lang = lang

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        if not self.database.user_in_seats(interaction.user) or interaction.user.id in [int(id_) for id_ in JsonHelper.get_user_id_list()]:
            ctx = await LangContext.get_context_from_interaction(bot=self.bot, interaction=interaction)

            await interaction.response.send_message(view=ConfirmationBookingView(ctx=ctx, lang=self.lang), ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(
                embed=Localization.translatable_embed(discord.Embed(), key="embed.user_in_seat", lang=self.lang),
                ephemeral=True, delete_after=5)


class StartBookingView(ui.LayoutView):
    def __init__(self, bot: Bot, lang: str):
        super().__init__(timeout=None)

        container = ui.Container()
        container.add_item(ui.TextDisplay(f"# {Localization.translatable('layout.ticket_booking.title', lang)}"))
        container.add_item(ui.TextDisplay(Localization.translatable("layout.ticket_booking.description", lang)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.MediaGallery(MediaGalleryItem(media=Localization.translatable("layout.ticket_booking.image", lang))))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.ActionRow(StartBookingButton(bot=bot, lang=lang)))

        self.add_item(container)


class StartVIPBookingView(ui.LayoutView):
    def __init__(self, bot: Bot, lang: str):
        super().__init__(timeout=None)

        container = ui.Container()
        container.add_item(ui.TextDisplay(f"# {Localization.translatable('layout.ticket_booking.title_vip', lang)}"))
        container.add_item(ui.TextDisplay(Localization.translatable("layout.ticket_booking.description_vip", lang)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.MediaGallery(MediaGalleryItem(media=Localization.translatable("layout.ticket_booking.image_vip", lang))))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.ActionRow(ui.Button(label="Купить VIP", style=discord.ButtonStyle.gray, url="https://boosty.to/ppvteam/purchase/3689630?ssource=DIRECT&share=subscription_link")))

        self.add_item(container)


class ConfirmationBookingView(ui.LayoutView):
    def __init__(self, ctx: Context, lang: str):
        super().__init__(timeout=None)

        container = ui.Container()
        container.add_item(ui.TextDisplay(Localization.translatable("layout.booking_confirm.description", lang)))
        container.add_item(ui.ActionRow(BookingTicketButton(ctx, lang)))

        self.add_item(container)


class ChoiseFloorView(ui.LayoutView):
    def __init__(self, ctx: Context, lang: str):
        database = TicketBookingDatabase()

        super().__init__(timeout=None)

        container = ui.Container()
        container.add_item(ui.Section(ui.TextDisplay(f"# {JsonHelper.get_floor_menu().get('title').get(lang)}"), accessory=ReloadButton(ctx=ctx, lang=lang)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.MediaGallery(MediaGalleryItem(media=JsonHelper.get_floor_menu().get('image').get(lang))))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        current_row = ui.ActionRow()
        row_counter = 1

        for floor in JsonHelper.get_seats():
            if len(current_row.children) >= 5:
                container.add_item(current_row)
                row_counter += 1
                current_row = ui.ActionRow(id=row_counter)

            button = FloorButton(ctx=ctx, lang=lang, floor=floor, disabled=not database.floor_is_available(floor))
            current_row.add_item(button)

        if current_row.children:
            container.add_item(current_row)

        container.add_item(ui.ActionRow(CloseTicketButton(ctx=ctx, lang=lang)))

        self.add_item(container)


class SeatView(ui.LayoutView):
    def __init__(self, ctx: Context, lang: str, floor: str, seat: str, disabled: bool = False):
        floor_data = FloorData(floor)
        seat_data = SeatData(floor, seat)

        super().__init__(timeout=None)

        container = ui.Container(accent_colour=floor_data.get_menu_color())
        container.add_item(ui.Section(ui.TextDisplay(f"# {seat}"), accessory=ReloadButton(ctx=ctx, lang=lang, disabled=disabled)))
        container.add_item(ui.TextDisplay(seat_data.get_description(lang=lang)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.MediaGallery(MediaGalleryItem(seat_data.get_image())))

        if seat_data.get_limit() is not None:
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            tickets_left = seat_data.get_limit() - len(seat_data.database.get_tickets_on_seat(floor, seat))
            limit = seat_data.get_limit() if seat_data.get_limit() < 9998 else "∞"
            container.add_item(ui.TextDisplay(f"**{Localization.translatable("layout.seat.tickets_limit", lang=lang)}: {len(seat_data.database.get_tickets_on_seat(floor, seat))}/{limit}{' 🔺' if tickets_left == 1 else ''}**"))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(
            ui.ActionRow(
                BackSeatButton(ctx=ctx, lang=lang, floor=floor, disabled=disabled),
                BackToFloorsButton(ctx=ctx, lang=lang, disabled=disabled),
                RentalSeatButton(ctx=ctx, lang=lang, floor=floor, seat=seat, disabled=disabled)
            )
        )

        self.add_item(container)


class ReloadButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, disabled: bool = False):
        super().__init__(emoji="🔁", style=discord.ButtonStyle.gray, custom_id=f"booking_reload_{ctx.interaction.user.id}", disabled=disabled)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang

    @interaction_error_handler(logger)
    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(view=ChoiseFloorView(ctx=self.ctx, lang=self.lang))


class FloorButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, floor: str, disabled: bool = False):
        super().__init__(label=f"{floor:⠀^12}", style=discord.ButtonStyle.gray, custom_id=f"floor_{floor}_{ctx.interaction.user.id}", disabled=disabled)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang
        self.floor = floor

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ChoiseSeatView(ctx=self.ctx, lang=self.lang, floor=self.floor))


class CloseTicketButton(ui.Button):
    def __init__(self, ctx: Context, lang: str):
        self.ticket = TicketSystem(ctx.bot)

        super().__init__(label=f"{Localization.translatable('button.close_ticket', lang=lang):⠀^62}", style=discord.ButtonStyle.gray, custom_id=f"close_ticket_{ctx.interaction.user.id}")

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await self.ticket.close_ticket(channel=interaction.channel)
        await interaction.channel.delete()


class ChoiseSeatView(ui.LayoutView):
    def __init__(self, ctx: Context, lang: str, floor: str, page: int = 0):
        self.database = TicketBookingDatabase()

        super().__init__(timeout=None)

        self.ctx = ctx
        self.lang = lang
        self.floor = floor
        self.page = page

        self.floor_data = FloorData(floor)

        self.seats_list = self.floor_data.get_seats()

        self.seats_per_page = 16
        self.start_idx = self.page * self.seats_per_page
        self.end_idx = self.start_idx + self.seats_per_page
        self.paginated_seats = self.seats_list[self.start_idx:self.end_idx]

        self.main_container = ui.Container(accent_colour=self.floor_data.get_menu_color())

        self._create_header()
        self._add_seats()
        self._add_pagination()

        self.add_item(self.main_container)

    def _create_header(self):
        self.main_container.add_item(ui.Section(ui.TextDisplay(f"# {self.floor_data.get_menu_title(self.lang)}"), accessory=ReloadButton(ctx=self.ctx, lang=self.lang)))
        self.main_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.main_container.add_item(ui.MediaGallery(MediaGalleryItem(self.floor_data.get_menu_image())))
        self.main_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

    def _add_seats(self):
        current_row = ui.ActionRow()
        row_counter = 1

        for seat in self.paginated_seats:
            if len(current_row.children) >= 5:
                self.main_container.add_item(current_row)
                row_counter += 1
                current_row = ui.ActionRow(id=row_counter)

            button = SeatButton(ctx=self.ctx, lang=self.lang, floor=self.floor, seat=seat.seat)
            current_row.add_item(button)

        if current_row.children:
            self.main_container.add_item(current_row)

    def _add_pagination(self):
        nav_row = ui.ActionRow()

        self.main_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        prev_button = discord.ui.Button(
            emoji="⬅",
            style=discord.ButtonStyle.gray,
            custom_id=f'seat_prev_{self.page - 1}_{self.ctx.interaction.user.id}',
            disabled=not self.page > 0
        )
        prev_button.callback = self.prev_callback

        next_button = discord.ui.Button(
            emoji="➡",
            style=discord.ButtonStyle.gray,
            custom_id=f'seat_next_{self.page + 1}_{self.ctx.interaction.user.id}',
            disabled=not self.end_idx < len(self.seats_list)
        )
        next_button.callback = self.next_callback

        nav_row.add_item(prev_button)
        nav_row.add_item(BackToFloorsButton(ctx=self.ctx, lang=self.lang))
        nav_row.add_item(next_button)

        self.main_container.add_item(nav_row)

    @interaction_error_handler(logger)
    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ChoiseSeatView(ctx=self.ctx, lang=self.lang, floor=self.floor, page=self.page - 1))

    @interaction_error_handler(logger)
    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ChoiseSeatView(ctx=self.ctx, lang=self.lang, floor=self.floor, page=self.page + 1))


class BackToFloorsButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, disabled: bool = False):
        super().__init__(emoji="🏠", style=discord.ButtonStyle.gray, custom_id=f"back_to_floors_{ctx.interaction.user.id}", disabled=disabled)
        self.ctx = ctx
        self.lang = lang

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ChoiseFloorView(self.ctx, lang=self.lang))


class BackSeatButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, floor: str, disabled: bool = False):
        super().__init__(emoji='⬅', style=discord.ButtonStyle.gray, custom_id=f"back_to_floor_{ctx.interaction.user.id}", disabled=disabled)
        self.ctx = ctx
        self.lang = lang
        self.floor = floor

    @interaction_error_handler(logger)
    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(view=ChoiseSeatView(ctx=self.ctx, lang=self.lang, floor=self.floor))


class SeatButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, floor: str, seat: str):
        seat_data = SeatData(floor=floor, seat=seat)

        super().__init__(label=str(seat), style=discord.ButtonStyle.gray,
                         custom_id=f"{seat}_{ctx.interaction.user.id}",
                         disabled=seat_data.is_bookable())

        self.ctx = ctx
        self.lang = lang
        self.floor = floor
        self.seat = seat

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=SeatView(ctx=self.ctx, lang=self.lang, floor=self.floor, seat=self.seat))


class RentalSeatButton(ui.Button):
    def __init__(self, ctx: Context, lang: str, floor: str, seat: str, disabled: bool = False):
        super().__init__(label=Localization.translatable("button.book_ticket", lang), style=discord.ButtonStyle.green, custom_id=f'{seat}_rental_{ctx.interaction.user.id}', disabled=disabled)

        self.ctx = ctx
        self.lang = lang
        self.floor = floor
        self.seat = seat

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayersModal(ctx=self.ctx, lang=self.lang, floor=self.floor, seat=self.seat, message=interaction.message))


class RentalRequestView(ui.View):
    def __init__(self, ctx: Context, lang: str, ticket_data: dict, disabled: bool = False):
        self.database = TicketBookingDatabase()
        self.ticket = TicketSystem(bot=ctx.bot)
        self.ticket_data: dict = ticket_data

        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self.lang = lang

        self.channel: discord.TextChannel = ticket_data.get('channel')
        self.floor: str = ticket_data.get('floor')
        self.seat: str = ticket_data.get('value')
        self.user: discord.User = ticket_data.get('user')
        self.players: str = ticket_data.get('players')

        reject_button = discord.ui.Button(label="Отклонить", style=discord.ButtonStyle.red, custom_id=f"reject_seat_{ctx.interaction.user.id}", disabled=disabled)
        reject_button.callback = self.reject_callback

        approve_button = discord.ui.Button(label='Одобрить', style=discord.ButtonStyle.green, custom_id=f"approve_seat_{ctx.interaction.user.id}", disabled=disabled)
        approve_button.callback = self.approve_callback

        self.add_item(reject_button)
        self.add_item(approve_button)

    @is_moderator
    @interaction_error_handler(logger)
    async def reject_callback(self, interaction: discord.Interaction):
        member = get(interaction.guild.members, name=self.channel.name.split('-')[2])
        self.database.remove_user(floor=self.floor, seat=self.seat, user_id=member.id)
        await self.ticket.close_ticket(self.channel)
        await self.channel.delete(reason="Тикет отклонён")

        self.database.set_seat_status(self.floor, self.seat, True)

        interaction.message.embeds[0].set_footer(text="Статус: 💀")
        embed = interaction.message.embeds[0]

        await interaction.response.edit_message(embed=embed, view=RentalRequestView(ctx=self.ctx, lang=self.lang, disabled=True, ticket_data=self.ticket_data))

        embed = Localization.translatable_embed(APPLICATION_REJECTED_EMBED, "embed.applivation_rejected", self.lang)
        embed.description = embed.description.format(self.seat)
        await self.user.send(embed=embed)

    @is_moderator
    @interaction_error_handler(logger)
    async def approve_callback(self, interaction: discord.Interaction):
        member = get(interaction.guild.members, name=self.channel.name.split('-')[2])
        interaction.message.embeds[0].set_footer(text="Статус: ✅")
        embed = interaction.message.embeds[0]
        await interaction.response.edit_message(embed=embed, view=RentalRequestView(ctx=self.ctx, lang=self.lang, disabled=True, ticket_data=self.ticket_data))

        if JsonHelper.get_booking_mode() in SeatModes.single_seats():
            self.database.set_seat_status(self.floor, self.seat, False)

        await member.add_roles(get(interaction.guild.roles, id=Language.lang_role_get(self.lang)))

        self.database.set_booking_status(floor=self.floor, seat=self.seat, user_id=member.id, status=BookingStatus.CONFIRMED)

        await self.channel.send(self.user.mention, embed=Localization.translatable_embed(SEAT_RESERVED_EMBED, key="embed.seat_reserved", lang=self.lang))
        await self.channel.set_permissions(member, read_messages=True, send_messages=False)
        await self.ticket.close_ticket(self.channel)


class AddPlayersModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label="modal_label.player_list",
        placeholder="modal_placeholder.prompt",
        custom_id=f"players_list",
        style=TextStyle.long,
        max_length=100
    )

    def __init__(self, *, ctx: Context, lang: str, floor: str, seat: str, message: discord.Message):
        self.database = TicketBookingDatabase()

        super().__init__(title=Localization.translatable("modal_title.player_list", lang), timeout=None, custom_id=f"add_players_{ctx.interaction.user.id}")

        self.ctx = ctx
        self.lang = lang

        self.players.label = Localization.translatable(self.players.label, lang)
        self.players.placeholder = Localization.translatable(self.players.placeholder, lang)

        self.message = message
        self.floor = floor
        self.seat = seat

    @interaction_error_handler(logger)
    async def on_submit(self, interaction: discord.Interaction):
        channel = get(interaction.guild.channels, id=config.CONFIRMATION_CHANNEL_ID)

        embed = discord.Embed(title="Заявка", description=f"{interaction.user.mention} подал заяву на бронирования места **{self.seat}**")
        embed.set_author(name=interaction.channel.name, url=interaction.channel.jump_url, icon_url=interaction.user.avatar.url)
        embed.add_field(name="Приглашенные игроки:", value=f"```{self.players.value}```", inline=False)
        embed.set_footer(text="Статус: ❌")

        await self.message.edit(view=SeatView(ctx=self.ctx, lang=self.lang, floor=self.floor, seat=self.seat, disabled=True))
        await interaction.response.send_message(embed=Localization.translatable_embed(discord.Embed(), "embed.moderators_notification", lang=self.lang))

        ticket_data = {'channel': interaction.channel, 'floor': self.floor, 'value': self.seat, 'user': interaction.user, 'players': self.players.value.split(' ')}

        self.database.add_user(self.floor, self.seat, players={str(interaction.user.id): ticket_data.get("players")}, status=BookingStatus.NOT_CONFIRMED)

        await interaction.channel.set_permissions(get(interaction.guild.members, id=interaction.user.id), read_messages=True, send_messages=True)
        await channel.send(content=f"<@{'> <@'.join(JsonHelper.get_user_id_list())}>")
        await channel.send(embed=embed, view=RentalRequestView(ctx=self.ctx, lang=self.lang, ticket_data=ticket_data))

        if JsonHelper.get_booking_mode() in SeatModes.single_seats():
            self.database.set_seat_status(self.floor, self.seat, False)

        logger.info(f"Информация о тикете {interaction.user.name}: {ticket_data}")
