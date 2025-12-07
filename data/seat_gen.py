import json
import re

from data.database import TicketBookingDatabase
from data.extract_json import JsonExtract
from data.seat_data import SeatModes


def generate_seats():
    seats1 = {
        "mode": SeatModes.STADIUM.value,
        "menu": {
            "title": {
                "en": "Select the sector you want to sit in",
                "ru": "Выберите сектор на котором хотите сидеть"
            },
            "description": {
                "en": "",
                "ru": "Выберите место на котором хотите сидеть. Заблокированные кнопки мест означают, что место уже забронировано."
            },
            "image": {
                "en": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&",
                "ru": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&"
            },
        },
        "floor": {
            "A": {
                "menu": {
                    "title": {
                        "en": "A Sector",
                        "ru": "A сектор"
                    },
                    "description": {
                        "en": "Choose the zone where you want to sit. The locked zone buttons mean that the zone is already booked.",
                        "ru": "Выберите зону, в которой хотите сидеть. Заблокированные кнопки зон означают, что зона уже забронирована."
                    },
                    "color": "fe8701",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&",
                },
                "list": {}
            },
            "B": {
                "menu": {
                    "title": {
                        "en": "B Sector",
                        "ru": "B сектор"
                    },
                    "description": {
                        "en": "Choose the zone where you want to sit. The locked zone buttons mean that the zone is already booked.",
                        "ru": "Выберите зону, в которой хотите сидеть. Заблокированные кнопки зон означают, что зона уже забронирована."
                    },
                    "color": "fe8701",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&",
                },
                "list": {}
            },
            "C": {
                "menu": {
                    "title": {
                        "en": "C Sector",
                        "ru": "C сектор"
                    },
                    "description": {
                        "en": "Choose the zone where you want to sit. The locked zone buttons mean that the zone is already booked.",
                        "ru": "Выберите зону, в которой хотите сидеть. Заблокированные кнопки зон означают, что зона уже забронирована."
                    },
                    "color": "fe8701",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&",
                },
                "list": {}
            },

            "FANZONE": {
                "menu": {
                    "title": {
                        "en": "FANZONE",
                        "ru": "FANZONE"
                    },
                    "description": {
                        "en": "Choose the zone where you want to sit. The locked zone buttons mean that the zone is already booked.",
                        "ru": "Выберите зону, в которой хотите сидеть. Заблокированные кнопки зон означают, что зона уже забронирована."
                    },
                    "color": "fe8701",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1446145263587819591/67856.png?ex=6932eb3a&is=693199ba&hm=55beb6e19bbf6946cfb6f017113a4039294ce71e97a26fecb41e2bb3032ac42a&",
                },
                "list": {}
            }
        }
    }

    with open("./seats_billie_eilish.json", 'r+', encoding="utf-8") as file:
        seats = json.load(file)

    seats["menu"]['image'] = {
                "en": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png",
                "ru": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png"
            },

    seats["floor"]["A"]["menu"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png"
    seats["floor"]["B"]["menu"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163658966302883/B.png"
    seats["floor"]["C"]["menu"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163679589564447/C.png"
    seats["floor"]["FANZONE"]["menu"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163697889443932/FANZONE.png"

    for i in range(1, 17):
        seats["floor"]["A"]["list"][f"{i}A"]["color"] = "fe8701"
        seats["floor"]["A"]["list"][f"{i}A"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png"

    for i in range(1, 17):
        seats["floor"]["B"]["list"][f"{i}B"]["color"] = "fe8701"
        seats["floor"]["B"]["list"][f"{i}B"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163658966302883/B.png"

    for i in range(1, 33):
        seats["floor"]["C"]["list"][f"{i}C"]["color"] = "fe8701"
        seats["floor"]["C"]["list"][f"{i}C"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163679589564447/C.png"

    for i in range(1, 3):
        seats["floor"]["FANZONE"]["list"][f"{i}"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163697889443932/FANZONE.png"

    for i in range(1, 23):
        seats["floor"]["VIP"]["list"][f"{i}"] = {
                    "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билета можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    },
                    "color": "0b9fe9",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1446825629256515615/V.I.P..png",
                    "limit": 1
                }

    return seats


def is_ordered(data):
    return all(data[i] <= data[i+1] for i in range(len(data) - 1))


def test_seats():
    with open("./seats.json", "r+", encoding="utf-8") as file:
        data = json.load(file)
    g = []
    for sector, a in data.get("floor").items():
        for i, j in a.items():
            g.append(i)

    f = [int(''.join(filter(lambda x: x.isdigit(), x))) for x in g]
    print(f)
    return is_ordered(g)


if __name__ == "__main__":
    with open("./seats.json", "w+", encoding="utf-8") as file:
        json.dump(generate_seats(), file, indent=4, ensure_ascii=False)

    database = TicketBookingDatabase()

