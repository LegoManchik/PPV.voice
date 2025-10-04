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


class SeatData:
    def __init__(self, floor: str, seat: str = None):
        with open("data/seats.json", 'r', encoding='utf-8') as json_file:
            self.data = json.load(json_file)

            self.floor = self.data.get('floor').get(floor).get("list")
            self.menu = self.data.get("floor").get(floor).get("menu")
            self.seat = self.data.get("floor").get(floor).get("list").get(seat)

    def get(self) -> dict:
        return self.data

    def get_seats(self) -> dict:
        return self.floor

    def get_seat_description(self, lang: str):
        return self.seat.get("description").get(lang)

    def get_seat_image(self) -> str:
        return self.seat.get("image")

    def get_menu_color(self) -> int:
        return int(self.menu.get("color"), 16)

    def get_menu_title(self, lang: str) -> str:
        return self.menu.get("title").get(lang)

    def get_menu_description(self, lang: str) -> str:
        return self.menu.get("description").get(lang)

    def get_menu_image(self) -> str:
        return self.menu.get("image")
