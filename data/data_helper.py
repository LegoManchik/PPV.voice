import os
import enum
import json
import functools
from dataclasses import dataclass

from config import TEMPLATE_PATH

from data.database import TicketBookingDatabase, SeatStatus
from data.data_classes.seat import Seat


class FloorData:
    def __init__(self, floor: str):
        self.database = TicketBookingDatabase()
        self.floor = floor
        self.floor_params = self._load()

        self.menu = self.floor_params.get("menu")

    def _load(self) -> dict:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as json_file:
            return json.load(json_file).get("floor").get(self.floor)

    def get_seats(self) -> list[Seat]:
        return self.database.get_seat_list(self.floor)

    def is_available(self) -> bool:
        return self.database.floor_is_available(self.floor)

    def set_status(self, status: bool):
        self.database.set_floor_status(self.floor, status)

    def get_menu_color(self) -> int:
        return int(self.menu.get("color"), 16)

    def get_menu_title(self, lang: str) -> str:
        return self.menu.get("title").get(lang)

    def get_menu_description(self, lang: str) -> str:
        return self.menu.get("description").get(lang)

    def get_menu_image(self) -> str:
        return self.menu.get("image")


class SeatData:
    def __init__(self, floor: str, seat: str, database: TicketBookingDatabase = None):
        self.database = database or TicketBookingDatabase()
        self.floor = floor
        self.seat = seat

        self.seat_data = None
        self.seat_params = None
        self._load()

    def _load(self):
        if self.seat:
            self.seat_data = self.database.get_seat(self.floor, self.seat)
        self.seat_params = self._load_params()

    def _load_params(self) -> dict:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as json_file:
            return json.load(json_file).get("floor").get(self.floor).get("list").get(self.seat)

    def refresh(self):
        self.seat_data = self.database.get_seat(self.floor, self.seat)

    def get_key(self) -> str:
        self.refresh()
        return self.seat_data.seat

    def get_players(self) -> dict[str]:
        self.refresh()
        return self.seat_data.players

    def is_available(self) -> bool:
        self.refresh()
        return self.seat_data.status

    def set_status(self, status: bool):
        self.database.set_seat_status(self.floor, self.seat, status)
        self.refresh()

    def is_bookable(self) -> bool:
        return ((len(self.database.get_tickets_on_seat(self.floor, self.get_key())) >= self.get_limit()) or not self.is_available())

    def get_description(self, lang: str) -> str:
        return self.seat_params.get("description").get(lang)

    def get_image(self) -> str:
        return self.seat_params.get("image")

    def get_limit(self) -> int:
        return self.seat_params.get("limit")

