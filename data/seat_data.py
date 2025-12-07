import os
import enum
import json


class SeatModes(enum.Enum):
    STANDART = "std"  # max 1 ticket
    STADIUM = "stadium"  # 1++ tickets

    @classmethod
    def single_seats(cls):
        return [cls.STANDART.value]

    def get_modes(self):
        return self.__dict__


class BookingStatus(enum.Enum):
    CONFIRMED = "confirmed"
    NOT_CONFIRMED = "not_confirmed"


class SeatData:
    def __init__(self, floor: str, seat: str = None):
        current_dir = os.path.dirname(os.path.abspath(__file__))

        seats_path = os.path.join(current_dir, "seats.json")

        with open(seats_path, 'r', encoding='utf-8') as json_file:
            self.data = json.load(json_file)

            self.floor = self.data.get('floor').get(floor).get("list")
            self.menu = self.data.get("floor").get(floor).get("menu")
            self.seat = self.floor.get(seat)

    def get(self) -> dict:
        return self.data

    def get_seats(self) -> dict:
        return self.floor

    def get_seat_description(self, lang: str):
        return self.seat.get("description").get(lang)

    def get_seat_image(self) -> str:
        return self.seat.get("image")

    def get_limit(self) -> int:
        return self.seat.get("limit")

    def get_menu_color(self) -> int:
        return int(self.menu.get("color"), 16)

    def get_menu_title(self, lang: str) -> str:
        return self.menu.get("title").get(lang)

    def get_menu_description(self, lang: str) -> str:
        return self.menu.get("description").get(lang)

    def get_menu_image(self) -> str:
        return self.menu.get("image")
