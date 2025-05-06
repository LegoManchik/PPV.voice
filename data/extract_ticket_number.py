import json
import random


class NonUniqueNumber(Exception):
    pass


class ExtractTicketNumber:
    @classmethod
    def get_random_number(cls):
        with open("data/tickets.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
        try:
            number = random.randint(1, 10001)
            if number in data:
                raise NonUniqueNumber
        except NonUniqueNumber:
            return ExtractTicketNumber.get_random_number()

        return number

    @classmethod
    def add_number(cls, number: int):
        with open("data/tickets.json", "r+", encoding="utf-8") as f:
            data: list = json.load(f)
            data.append(number)
            f.seek(0)
            json.dump(data, f)
