import json


class SeatData:
    def __init__(self, floor: int, seat: str = None):
        with open("seats.json", 'r', encoding='utf-8') as json_file:
            self.data = json.load(json_file)

            self.floor = self.data.get('floor').get(str(floor))
            self.seat = self.data.get('floor').get(str(floor)).get(seat)

    def get(self):
        return self.data

    def get_seats(self):
        return self.floor

    def get_description(self, lang: str):
        return self.seat.get('description').get(lang)

    def get_image(self):
        return self.seat.get('image')

    def get_color(self):
        return self.seat.get('color')
