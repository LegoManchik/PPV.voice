import json
import random


class NonUniqueNumber(Exception):
    pass


class JsonExtract:
    @classmethod
    def get_random_number(cls):
        with open("data/tickets.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
        try:
            number = random.randint(1, 10001)
            if number in data:
                raise NonUniqueNumber
        except NonUniqueNumber:
            return JsonExtract.get_random_number()

        return number

    @classmethod
    def add_number(cls, number: int):
        with open("data/tickets.json", "r+", encoding="utf-8") as f:
            data: list = json.load(f)
            data.append(number)
            f.seek(0)
            json.dump(data, f)

    @classmethod
    def get_user_id_list(cls):
        with open("data/ping_users.json", "r+", encoding="utf-8") as f:
            data = json.load(f)

        return list(map(str, data))
