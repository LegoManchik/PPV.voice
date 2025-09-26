import json
import os
import random


class NonUniqueNumber(Exception):
    pass


class JsonExtract:
    @classmethod
    def get_seats(cls) -> dict:
        seats = {}
        with open("data/seats.json", "r+", encoding="utf-8") as file:
            data = json.load(file).get("floor")
            for key, value in data.items():
                seats[key] = value.get("list")

        return seats

    @classmethod
    def get_floor_menu(cls) -> dict:
        with open("data/seats.json", "r+", encoding="utf-8") as file:
            return json.load(file).get("menu")

    @classmethod
    def get_random_number(cls) -> int:
        with open("data/tickets.json", "r+", encoding="utf-8") as file:
            data = json.load(file)
        try:
            number = random.randint(1, 10001)
            if number in data:
                raise NonUniqueNumber
        except NonUniqueNumber:
            return JsonExtract.get_random_number()

        return number

    @classmethod
    def get_user_id_list(cls) -> list[str]:
        with open("data/ping_users.json", "r+", encoding="utf-8") as file:
            data = json.load(file)

        return list(map(str, data))

    @classmethod
    def add_number(cls, number: int):
        with open("data/tickets.json", "r+", encoding="utf-8") as file:
            data: list = json.load(file)
            data.append(number)
            file.seek(0)
            json.dump(data, file)
