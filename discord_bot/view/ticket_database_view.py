import random

import discord
from discord import ui, TextStyle, ButtonStyle

from discord_bot import config
from discord_bot.data.database import TicketBookingDatabase, SeatStatus
from discord_bot.data.extract_json import JsonExtract
from discord_bot.data.seat_data import SeatData
from discord_bot.utils.logger import BotLogger, interaction_error_handler
from discord_bot.utils.localization import Localization


logger = BotLogger().get_file_logger(__name__)


class DatabaseMenuView(ui.LayoutView):
    def __init__(self, floor: str = list(JsonExtract.get_seats().keys())[0], page: int = 0, search: bool = False):
        super().__init__()
        self.database = TicketBookingDatabase()
        self.floor = floor
        self.page = page
        self.search = search
        self.rows_per_page = 5

        self.data = self.database.get_seat_list(floor=self.floor)
        self.total_pages = (len(self.data) + self.rows_per_page - 1) // self.rows_per_page if self.data else 1

        self.start_idx = self.page * self.rows_per_page
        self.end_idx = self.start_idx + self.rows_per_page
        self.page_data = self.data[self.start_idx:self.end_idx]

        self._create_layout()
        self._add_pagination()

    def _create_layout(self):
        container = ui.Container()
        floor_select_row = ui.ActionRow()

        floor_select = ui.Select(
            placeholder="Выберите этаж...",
            options=[
                discord.SelectOption(label=f"Этаж {x}", value=x, emoji="🔹", default=self.floor == x) for x in JsonExtract.get_seats()
            ],
            custom_id="floor_select"
        )
        floor_select.callback = self._floor_select_callback
        floor_select_row.add_item(floor_select)
        container.add_item(floor_select_row)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"-# 📄 Страница {self.page + 1}/{self.total_pages}{'':\t^17}👥 Занятые места: {abs(self.database.avalibles_seats(floor=self.floor)[0] - self.database.avalibles_seats(floor=self.floor)[1])}/{self.database.avalibles_seats(floor=self.floor)[1]}"))

        self.add_item(container)

        for seat in self.page_data:
            self.add_item(self._create_seat_row(seat))

    def _create_seat_row(self, seat: tuple) -> ui.Container:
        seat_container = ui.Container(accent_colour=int(SeatData(floor=self.floor).get_menu_color()))

        user = f"<@{seat[1]}>" if seat[1] is not None else f"<@&{config.NONE_ROLE_ID}>"

        status = "✅"

        avalible = self.database.is_avalible(self.floor, seat[0])

        if not avalible:
            if seat[1] is None:
                status = "🟨"
            else:
                status = "🟥"

            action_button = ui.Button(
                label="Редактировать",
                style=ButtonStyle.gray,
                custom_id=f"edit_{seat[0]}"
            )
            action_button.callback = self._edit_button_callback
        else:
            action_button = ui.Button(
                emoji="➕",
                style=ButtonStyle.green,
                custom_id=f"add_{seat[0]}"
            )
            action_button.callback = self._add_button_callback

        place_display = ui.TextDisplay(f">>> {status} | **{seat[0]}** | {user}\n-# Ники игроков: {seat[2]}")

        seat_container.add_item(ui.Section(place_display, accessory=action_button))

        return seat_container

    def _add_pagination(self):
        pagination_container = ui.Container()
        pagination_row = ui.ActionRow()

        prev_button = ui.Button(
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"prev_{self.floor}_{self.page}",
            disabled=self.page == 0
        )
        prev_button.callback = self._prev_page_callback

        next_button = ui.Button(
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"next_{self.floor}_{self.page}",
            disabled=self.page == self.total_pages - 1
        )
        next_button.callback = self._next_page_callback

        pagination_row.add_item(prev_button)
        pagination_row.add_item(next_button)

        pagination_container.add_item(pagination_row)
        self.add_item(pagination_container)

    @interaction_error_handler(logger)
    async def _floor_select_callback(self, interaction: discord.Interaction):
        selected_floor = interaction.data["values"][0]
        new_view = DatabaseMenuView(selected_floor)
        await interaction.response.edit_message(view=new_view)

    @interaction_error_handler(logger)
    async def _prev_page_callback(self, interaction: discord.Interaction):
        if self.page > 0:
            new_view = DatabaseMenuView(self.floor, self.page - 1, search=self.search)
            await interaction.response.edit_message(view=new_view)
        else:
            await interaction.response.defer()

    @interaction_error_handler(logger)
    async def _next_page_callback(self, interaction: discord.Interaction):
        if self.page < self.total_pages - 1:
            new_view = DatabaseMenuView(self.floor, self.page + 1, search=self.search)
            await interaction.response.edit_message(view=new_view)
        else:
            await interaction.response.defer()

    @interaction_error_handler(logger)
    async def _edit_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=EditSeat(message=interaction.message, floor=self.floor, seat=interaction.data.get("custom_id").split("_")[-1], page=self.page), ephemeral=True)

    @interaction_error_handler(logger)
    async def _add_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=AddUserView(message=interaction.message, floor=self.floor, seat=interaction.data.get("custom_id").split("_")[-1], page=self.page), ephemeral=True)


class EditSeat(ui.LayoutView):
    def __init__(self, message: discord.Message, floor: str, seat: str, page: int = 0):
        super().__init__()
        self.message = message

        self.database = TicketBookingDatabase()
        self.floor = floor
        self.seat = seat
        self.page = page

        status = "✅"

        avalible = self.database.is_avalible(self.floor, seat)

        self.seat_data = self.database.get_seat(self.floor, self.seat)[0]

        if not avalible:
            if self.seat_data[1] is None:
                status = "🟨"
            else:
                status = "🟥"

        container = ui.Container()
        container.add_item(ui.TextDisplay(f">>> {status} | **{seat}** | <@{self.seat_data[1]}>\n-# Ники игроков: {self.seat_data[2]}"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        back_button = discord.ui.Button(
            emoji="⬅",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_back"
        )
        back_button.callback = self._back_callback

        cancel_reservetion_button = discord.ui.Button(
            label="Отменить бронь",
            emoji="🚩",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_cancel_reservetion"
        )
        cancel_reservetion_button.callback = self._cancel_reservetion_callback

        reset_status_button = discord.ui.Button(
            label="Разблокировать место",
            emoji="🔄",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_reset_status",
            disabled=self.seat_data[1] is not None and not avalible
        )
        reset_status_button.callback = self._reset_status_callback

        action_row = ui.ActionRow(back_button, cancel_reservetion_button, reset_status_button)

        container.add_item(action_row)
        self.add_item(container)

    @interaction_error_handler(logger)
    async def _back_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()

    @interaction_error_handler(logger)
    async def _cancel_reservetion_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.database.remove_user(self.floor, self.seat)
        self.database.set_seat_status(self.floor, self.seat, SeatStatus.AVAILABLE)
        await self.message.edit(view=DatabaseMenuView(floor=self.floor, page=self.page))
        await interaction.delete_original_response()

    @interaction_error_handler(logger)
    async def _reset_status_callback(self, interaction: discord.Interaction):
        self.database.set_seat_status(floor=self.floor, seat=self.seat, status=SeatStatus.AVAILABLE)
        await self.message.edit(view=DatabaseMenuView(floor=self.floor, page=self.page))
        await interaction.response.defer()


class UserSelect(discord.ui.UserSelect):
    def __init__(self, message: discord.Message, floor: str, seat: str, page: int):
        self.message = message
        self.floor = floor
        self.seat = seat
        self.page = page

        super().__init__(
            custom_id='user_select',
            placeholder="Выберите пользователя...",
        )

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayersToDatabaseModal(message=self.message, floor=self.floor, seat=self.seat, user=self.values[0], page=self.page))
        await interaction.delete_original_response()


class AddUserView(ui.LayoutView):
    def __init__(self, message: discord.Message, floor: str, seat: str, page: int):
        super().__init__()

        container = ui.Container()

        container.add_item(ui.TextDisplay(">>> **Бронирование места**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.ActionRow(UserSelect(message=message, floor=floor, seat=seat, page=page)))

        self.add_item(container)


class AddPlayersToDatabaseModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label="modal_label.player_list",
        placeholder="modal_placeholder.prompt",
        custom_id=f"players_list",
        style=TextStyle.long,
        max_length=100
    )

    def __init__(self, *, timeout=None, floor: str, seat: str, page: int, user: discord.User, message: discord.Message):
        super().__init__(title=Localization.translatable("modal_title.player_list", "ru"), timeout=timeout, custom_id="add_players_database")

        self.players.label = Localization.translatable(self.players.label, "ru")
        self.players.placeholder = Localization.translatable(self.players.placeholder, "ru")

        self.message = message
        self.floor = floor
        self.seat = seat
        self.page = page
        self.user = user

        self.database = TicketBookingDatabase()

    @interaction_error_handler(logger)
    async def on_submit(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} отправил запрос {interaction.data.get('custom_id')}")
        self.database.add_user(self.floor, self.seat, self.user.id, self.players.value)
        self.database.set_seat_status(self.floor, self.seat, SeatStatus.UNAVAILABLE)
        await self.message.edit(view=DatabaseMenuView(floor=self.floor, page=self.page))
        await interaction.response.defer()
