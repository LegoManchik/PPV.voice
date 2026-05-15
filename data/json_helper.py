import json
import os
import random

from config import TEMPLATE_PATH


class NonUniqueNumber(Exception):
    pass


class JsonHelper:
    @classmethod
    def get_floors(cls) -> list:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            data = json.load(file).get("floor")
            return list(data.keys())

    @classmethod
    def get_seats(cls) -> dict:
        seats = {}
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            data = json.load(file).get("floor")
            for key, value in data.items():
                seats[key] = value.get("list")

        return seats

    @classmethod
    def get_floor_menu(cls) -> dict:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            return json.load(file).get("menu")

    @classmethod
    def get_booking_mode(cls) -> str:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            return json.load(file).get("mode")

    @classmethod
    def get_random_number(cls) -> int:
        with open("data/tickets.json", "r+", encoding="utf-8") as file:
            data = json.load(file)
        try:
            number = random.randint(1, 10001)
            if number in data:
                raise NonUniqueNumber
        except NonUniqueNumber:
            return JsonHelper.get_random_number()

        return number

    @classmethod
    def is_single_floor(cls) -> bool:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            return len(json.load(file).get("floor")) == 1

    @classmethod
    def is_single_seat(cls, floor: str) -> bool:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            return len(json.load(file).get("floor").get(floor).get("list")) == 1

    @classmethod
    def get_single_seat_key(cls, floor: str) -> str:
        with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
            seat_key = list(json.load(file).get("floor").get(floor).get("list").keys())[0]
            return seat_key

    @classmethod
    def add_number(cls, number: int):
        with open("data/tickets.json", "r+", encoding="utf-8") as file:
            data: list = json.load(file)
            data.append(number)
            file.seek(0)
            json.dump(data, file)

    @classmethod
    def get_user_id_list(cls) -> list[str]:
        with open("data/ping_users.json", "r+", encoding="utf-8") as file:
            return list(map(str, json.load(file)))

    @classmethod
    def add_user_in_list(cls, user_id: int) -> bool:
        data: list[int] = list(map(int, cls.get_user_id_list()))

        if user_id in data:
            return False

        data.append(user_id)

        with open("data/ping_users.json", "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
            return True

    @classmethod
    def remove_user_in_list(cls, user_id: int) -> bool:
        data: list[int] = list(map(int, cls.get_user_id_list()))

        if user_id not in data:
            return False

        data.remove(user_id)

        with open("data/ping_users.json", "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
            return True
