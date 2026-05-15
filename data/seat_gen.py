import json
import re

from data.database import TicketBookingDatabase
from data.json_helper import JsonHelper
from data.data_helper import SeatModes


def generate_seats():
    seats = {
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
            }
        }
    }

    seats["menu"]['image'] = {
                "en": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png",
                "ru": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png"
    }

    seats["floor"]["A"]["menu"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png"

    for i in range(1, 17):
        seats["floor"]["A"]["list"][f"{i}A"] = {
            "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    }
        }
        seats["floor"]["A"]["list"][f"{i}A"]["color"] = "fe8701"
        seats["floor"]["A"]["list"][f"{i}A"]["image"] = "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png"
        seats["floor"]["A"]["list"][f"{i}A"]["limit"] = 9999

    return seats


def is_ordered(data):
    return all(data[i] <= data[i+1] for i in range(len(data) - 1))


def test_seats():
    with open("seats.json", "r+", encoding="utf-8") as file:
        data = json.load(file)
    g = []
    for sector, a in data.get("floor").items():
        for i, j in a.items():
            g.append(i)

    f = [int(''.join(filter(lambda x: x.isdigit(), x))) for x in g]
    print(f)
    return is_ordered(g)


if __name__ == "__main__":
    with open("seats.json", "w+", encoding="utf-8") as file:
        json.dump(generate_seats(), file, indent=4, ensure_ascii=False)

    database = TicketBookingDatabase()

