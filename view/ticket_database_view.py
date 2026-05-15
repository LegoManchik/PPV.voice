import random

import discord
from discord import ui, TextStyle, ButtonStyle

import config
from data.database import TicketBookingDatabase, SeatStatus
from data.json_helper import JsonHelper
from data.enums import SeatModes, BookingStatus
from data.data_classes.seat import Seat
from data.data_helper import SeatData, FloorData
from utils.logger import BotLogger, interaction_error_handler
from utils.localization import Localization


logger = BotLogger().get_file_logger(__name__)


class DatabaseMenuView(ui.LayoutView):
    def __init__(self, floor: str = list(JsonHelper.get_seats().keys())[0], page: int = 0, search: bool = False):
        super().__init__()

        self.floor = floor
        self.page = page
        self.search = search
        self.rows_per_page = 5

        self.floor_data = FloorData(floor)
        self.database = TicketBookingDatabase()

        self.seats_list = self.floor_data.get_seats()
        self.total_pages = (len(self.seats_list) + self.rows_per_page - 1) // self.rows_per_page if self.seats_list else 1

        self.start_idx = self.page * self.rows_per_page
        self.end_idx = self.start_idx + self.rows_per_page
        self.page_data = self.seats_list[self.start_idx:self.end_idx]

        self.floor_available = self.floor_data.is_available()

        self._create_layout()
        self._add_pagination()

    def _create_layout(self):
        container = ui.Container()
        floor_select_row = ui.ActionRow()

        floor_select = ui.Select(
            placeholder="Выберите этаж...",
            options=[
                discord.SelectOption(label=f"Этаж {floor}", value=floor, emoji="⛔" if not self.floor_available else "🟩", default=self.floor == floor) for floor in JsonHelper.get_seats()
            ],
            custom_id="floor_select"
        )
        floor_select.callback = self._floor_select_callback

        floor_select_row.add_item(floor_select)

        container.add_item(floor_select_row)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        avalibles_seats = self.database.availables_seats(floor=self.floor)

        container.add_item(
            ui.TextDisplay(f"-# 📄 Страница: **{self.page + 1}/{self.total_pages}**{'':\t^5}{'🎫 Забронировано билетов:' + "**" + str(self.database.all_users_count(self.floor)) + "**" if JsonHelper.get_booking_mode() not in SeatModes.single_seats() else ''}{'':\t^5} ⛔ Закрытые места: **{abs(avalibles_seats[0] - avalibles_seats[1])}/{avalibles_seats[1]}**")
        )

        self.add_item(container)

        for seat in self.page_data:
            self.add_item(self._create_seat_row(seat))

    def _create_seat_row(self, value: Seat) -> ui.Container:
        seat_container = ui.Container(accent_colour=int(FloorData(self.floor).get_menu_color()))

        status = "✅" if value.status else "🟥"

        if len(value.players) != 0:
            action_button = ui.Button(
                label="Редактировать",
                style=ButtonStyle.gray,
                custom_id=f"edit_{value.seat}"
            )
            action_button.callback = self._edit_button_callback
        else:
            action_button = ui.Button(
                emoji="➕",
                style=ButtonStyle.green,
                custom_id=f"add_{value.seat}"
            )
            action_button.callback = self._add_button_callback

        users_list = [f"<@{key}> " for key, value in value.players.items()]

        users_info = ''.join(users_list[:2]) + f"{'...' if len(users_list) > 2 else ''}" if len(value.players.items()) != 0 else f"Место никем не забронировано"

        seat_info = f">>> {status} | **{value.seat}**\n-# {users_info}"

        place_display = ui.TextDisplay(seat_info)

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

        reset_status_button = discord.ui.Button(
            label="Закрыть бронь" if self.floor_available else "Открыть бронь",
            emoji="⛔" if self.floor_available else "✅",
            style=discord.ButtonStyle.red if self.floor_available else discord.ButtonStyle.green,
            custom_id="reset_floor_status",
        )
        reset_status_button.callback = self._reset_status_callback

        pagination_row.add_item(prev_button)
        pagination_row.add_item(next_button)
        pagination_row.add_item(reset_status_button)

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
        await interaction.response.send_message(view=EditSeat(message=interaction.message, floor=self.floor, seat=interaction.data.get("custom_id").split("_")[-1], main_page=self.page), delete_after=60)

    @interaction_error_handler(logger)
    async def _add_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=AddUserView(main_message=interaction.message, floor=self.floor, seat=interaction.data.get("custom_id").split("_")[-1], main_page=self.page), ephemeral=True)

    @interaction_error_handler(logger)
    async def _reset_status_callback(self, interaction: discord.Interaction):
        self.floor_data.set_status(status=not self.floor_available)
        await interaction.response.edit_message(view=DatabaseMenuView(floor=self.floor, page=self.page))


class EditSeat(ui.LayoutView):
    def __init__(self, message: discord.Message, floor: str, seat: str, main_page: int = 0, edit_page: int = 0):
        super().__init__()
        self.message = message

        self.seat_data = SeatData(floor=floor, seat=seat)

        self.floor = floor
        self.seat = seat
        self.main_page = main_page
        self.edit_page = edit_page

        self.rows_per_page = 5

        self.seats = list(self.seat_data.get_players().items())
        self.available = self.seat_data.is_available()

        self.total_pages = (len(self.seats) + self.rows_per_page - 1) // self.rows_per_page if self.seats else 1

        self.start_idx = self.edit_page * self.rows_per_page
        self.end_idx = self.start_idx + self.rows_per_page
        self.page_data = self.seats[self.start_idx:self.end_idx]

        self.container = ui.Container()

        self._add_layout()
        self._add_booking_list()

        if len(self.seats) > self.rows_per_page:
            self._add_pagination()

        self._add_action_buttons()

        self.add_item(self.container)

    def _add_layout(self):
        status = "✅" if self.available else "🟥"

        reload_button = ui.Button(
            emoji="🔁",
            style=discord.ButtonStyle.gray,
            custom_id="edit_reload"
        )
        reload_button.callback = self._reload_button_callback

        self.container.add_item(ui.Section(ui.TextDisplay(f"# {status} | **{self.seat}**\n"), accessory=reload_button))
        self.container.add_item(ui.TextDisplay(f"-# {f'📄 Страница: **{self.edit_page + 1}/{self.total_pages}**' if self.total_pages > 1 else ''}{'':\t^17} 🎫 Броней в секторе: **{len(self.seat_data.get_players())}{f'/{self.seat_data.get_limit()}' if self.seat_data.get_limit() is not None else ''}**"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

    def _status_emoji(self, status: str):
        return {"confirmed": "✅", "not_confirmed": "❌"}.get(status)

    def _add_booking_list(self):
        for key, value in self.page_data:
            cancel_reservetion_button = discord.ui.Button(
                label="Отменить бронь",
                emoji="🚩",
                style=discord.ButtonStyle.gray,
                custom_id=f"seat_edit_cancel_reservetion_{key}"
            )

            cancel_reservetion_button.callback = self._cancel_reservetion_callback

            self.container.add_item(
                ui.Section(
                    ui.TextDisplay(f">>> {self._status_emoji(value.get("status"))}<@{key}>\n-# Ники игроков: {' '.join(value.get("list"))}\n"),
                    accessory=cancel_reservetion_button)
            )
            self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    def _add_pagination(self):
        prev_button = ui.Button(
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"prev_{self.seat}_{self.edit_page}",
            disabled=self.edit_page == 0
        )
        prev_button.callback = self._prev_page_callback

        next_button = ui.Button(
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"next_{self.seat}_{self.edit_page}",
            disabled=self.edit_page == self.total_pages - 1
        )
        next_button.callback = self._next_page_callback

        pagination_row = ui.ActionRow(prev_button, next_button)

        self.container.add_item(pagination_row)

    def _add_action_buttons(self):
        back_button = discord.ui.Button(
            emoji="❌",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_back"
        )
        back_button.callback = self._back_callback
        database = TicketBookingDatabase()
        reset_status_button_disabled = len(database.get_players_on_seat(floor=self.floor, seat=self.seat)) == self.seat_data.get_limit()
        reset_status_button = discord.ui.Button(
            label="Лимит бронирования" if reset_status_button_disabled else "Закрыть бронь" if self.available else "Открыть бронь",
            emoji="⚠" if reset_status_button_disabled else "⛔" if self.available else "✅",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_reset_status",
            disabled=reset_status_button_disabled
        )
        reset_status_button.callback = self._reset_status_callback

        players_list_button = discord.ui.Button(
            emoji="📃",
            style=discord.ButtonStyle.gray,
            custom_id="seat_edit_players_list"
        )
        players_list_button.callback = self._players_list_callback

        action_button = ui.Button(
            emoji="➕",
            style=ButtonStyle.green,
            custom_id=f"add_{self.seat}_edit",
            disabled=not self.available
        )
        action_button.callback = self._add_button_callback

        action_row = ui.ActionRow(back_button, reset_status_button, players_list_button, action_button)

        self.container.add_item(action_row)

    @interaction_error_handler(logger)
    async def _reload_button_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=EditSeat(message=self.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=0))

    @interaction_error_handler(logger)
    async def _prev_page_callback(self, interaction: discord.Interaction):
        if self.edit_page > 0:
            new_view = EditSeat(self.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page - 1)
            await interaction.response.edit_message(view=new_view)
        else:
            await interaction.response.defer()

    @interaction_error_handler(logger)
    async def _next_page_callback(self, interaction: discord.Interaction):
        if self.edit_page < self.total_pages - 1:
            new_view = EditSeat(self.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page + 1)
            await interaction.response.edit_message(view=new_view)
        else:
            await interaction.response.defer()

    @interaction_error_handler(logger)
    async def _back_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()

    @interaction_error_handler(logger)
    async def _cancel_reservetion_callback(self, interaction: discord.Interaction):
        database = TicketBookingDatabase()
        database.remove_user(self.floor, self.seat, int(interaction.data.get("custom_id").split("_")[-1]))

        await self.message.edit(view=DatabaseMenuView(floor=self.floor, page=self.main_page))
        await interaction.response.edit_message(view=EditSeat(message=self.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page if len(self.page_data) != 1 else self.edit_page - 1 if self.edit_page > 0 else 0))

    @interaction_error_handler(logger)
    async def _reset_status_callback(self, interaction: discord.Interaction):
        self.seat_data.set_status(not self.available)
        await self.message.edit(view=DatabaseMenuView(floor=self.floor, page=self.main_page))
        await interaction.response.edit_message(view=EditSeat(message=self.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page))

    @interaction_error_handler(logger)
    async def _players_list_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=PlayersList(floor=self.floor, seat=self.seat), ephemeral=True)

    @interaction_error_handler(logger)
    async def _add_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=AddUserView(main_message=self.message, editmenu_message=interaction.message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page), ephemeral=True)


class PlayersList(discord.ui.LayoutView):
    def __init__(self, floor: str, seat: str):
        super().__init__()

        self.database = TicketBookingDatabase()
        self.floor = floor
        self.seat = seat

        self.players_list = self.database.get_players_on_seat(floor, seat)

        self.container = ui.Container()
        self._add_layout()
        self.add_item(self.container)

    def _add_layout(self):
        self.container.add_item(ui.TextDisplay(f"# 📃 | Список игроков сектора {self.seat}"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.container.add_item(ui.TextDisplay(f"{''.join([f'```{player}```\n' for player in self.players_list])}"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))


class UserSelect(discord.ui.UserSelect):
    def __init__(self, main_message: discord.Message, floor: str, seat: str, main_page: int, edit_page: int = 0, editmenu_message: discord.Message = None):
        self.main_message = main_message
        self.editmenu_message = editmenu_message
        self.floor = floor
        self.seat = seat
        self.main_page = main_page
        self.edit_page = edit_page

        super().__init__(
            custom_id='user_select',
            placeholder="Выберите пользователя...",
        )

    @interaction_error_handler(logger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayersToDatabaseModal(main_message=self.main_message, editmenu_message=self.editmenu_message, floor=self.floor, seat=self.seat, user=self.values[0], main_page=self.main_page, edit_page=self.edit_page))
        await interaction.delete_original_response()


class AddUserView(ui.LayoutView):
    def __init__(self, main_message: discord.Message, floor: str, seat: str, main_page: int, edit_page: int = 0, editmenu_message: discord.Message = None):
        super().__init__()

        container = ui.Container()

        container.add_item(ui.TextDisplay(">>> **Бронирование места**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.ActionRow(UserSelect(main_message=main_message, editmenu_message=editmenu_message, floor=floor, seat=seat, main_page=main_page, edit_page=edit_page)))

        self.add_item(container)


class AddPlayersToDatabaseModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label=Localization.translatable("modal_label.player_list", "ru"),
        placeholder=Localization.translatable("modal_placeholder.prompt", "ru"),
        custom_id=f"players_list",
        style=TextStyle.long,
        max_length=100
    )

    def __init__(self, *, timeout=None, floor: str, seat: str, main_page: int = 0, edit_page: int = 0, user: discord.User, main_message: discord.Message, editmenu_message: discord.Message = None):
        super().__init__(title=Localization.translatable("modal_title.player_list", "ru"), timeout=timeout, custom_id="add_players_database")

        self.floor = floor
        self.seat = seat

        self.user = user

        self.main_message = main_message
        self.editmenu_message = editmenu_message

        self.main_page = main_page
        self.edit_page = edit_page

        self.database = TicketBookingDatabase()

    @interaction_error_handler(logger)
    async def on_submit(self, interaction: discord.Interaction):
        if not self.database.user_on_seat(floor=self.floor, seat=self.seat, user_id=self.user.id):
            self.database.add_user(floor=self.floor, seat=self.seat, players={str(self.user.id): self.players.value.split(" ")}, status=BookingStatus.CONFIRMED)

            if self.editmenu_message is not None:
                await self.editmenu_message.edit(view=EditSeat(message=self.main_message, floor=self.floor, seat=self.seat, main_page=self.main_page, edit_page=self.edit_page))

            await self.main_message.edit(view=DatabaseMenuView(floor=self.floor, page=self.main_page))

            await interaction.response.defer()
        else:
            await interaction.response.send_message(embed=discord.Embed(description="У этого пользователя уже есть бронирование на это место", color=discord.Color.red()), ephemeral=True, delete_after=3)

