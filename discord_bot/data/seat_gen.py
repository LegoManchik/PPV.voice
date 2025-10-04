import json
import re

from discord_bot.data.database import TicketBookingDatabase
from discord_bot.data.extract_json import JsonExtract
from discord_bot.data.seat_data import SeatModes


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
                "en": "https://media.discordapp.net/attachments/1365977478157303839/1423992723534254131/Frame_1062145929_2.png?ex=68e25411&is=68e10291&hm=cd755f720e1ce03910bc9aa34202c9b3bcee2dfd96e04a208e7edb42e212666b&=&format=webp&quality=lossless&width=1572&height=884",
                "ru": "https://media.discordapp.net/attachments/1365977478157303839/1423992723534254131/Frame_1062145929_2.png?ex=68e25411&is=68e10291&hm=cd755f720e1ce03910bc9aa34202c9b3bcee2dfd96e04a208e7edb42e212666b&=&format=webp&quality=lossless&width=1572&height=884"
            },
        },
        "floor": {
            "R": {
                "menu": {
                    "title": {
                        "en": "Red Sector",
                        "ru": "Красный сектор"
                    },
                    "description": {
                        "en": "Choose the seat where you want to sit. The locked seat buttons mean that the seat has already been booked.",
                        "ru": "Выберите место на котором хотите сидеть. Заблокированные кнопки мест означают, что место уже забронировано."
                    },
                    "color": "ee5e5e",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992702399418479/Frame_1062145930_2.png?ex=68e2540c&is=68e1028c&hm=7e9d5c189ee512af5111b907c8c1373e317904a7d325858af7187590981521cb&",
                },
                "list": {}
            },
            "Y": {
                "menu": {
                    "title": {
                        "en": "Yellow Sector",
                        "ru": "Жёлтый сектор"
                    },
                    "description": {
                        "en": "Choose the seat where you want to sit. The locked seat buttons mean that the seat has already been booked.",
                        "ru": "Выберите место на котором хотите сидеть. Заблокированные кнопки мест означают, что место уже забронировано."
                    },
                    "color": "ffc525",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992680488243290/Frame_1062145931_2.png?ex=68e25407&is=68e10287&hm=c027233f6ff9cad464d99056174bf25ecae606b7d9a21f0ea249877df52830be&",
                },
                "list": {}
            },
            "W": {
                "menu": {
                    "title": {
                        "en": "White Sector",
                        "ru": "Белый сектор"
                    },
                    "description": {
                        "en": "Choose the seat where you want to sit. The locked seat buttons mean that the seat has already been booked.",
                        "ru": "Выберите место на котором хотите сидеть. Заблокированные кнопки мест означают, что место уже забронировано."
                    },
                    "color": "ffffff",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992659013402696/7869678_2.png?ex=68e25402&is=68e10282&hm=ed000ac0e181339c6dec13e624e305ffc3955c37b410ff22c88c61052df73f20&",
                },
                "list": {}
            },
            "P": {
                "menu": {
                    "title": {
                        "en": "Purple Sector",
                        "ru": "Фиолетовый этаж"
                    },
                    "description": {
                        "en": "Choose the seat where you want to sit. The locked seat buttons mean that the seat has already been booked.",
                        "ru": "Выберите место на котором хотите сидеть. Заблокированные кнопки мест означают, что место уже забронировано."
                    },
                    "color": "cb88ff",
                    "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992627224903792/6789_2.png?ex=68e253fa&is=68e1027a&hm=448a7c040a1dea368993b2579064459d3cb45f59dc4a06dc8585283d3e958ffb&",
                },
                "list": {}
            }
        }
    }

    for i in range(1, 201):
        if 0 < i < 45:
            seats["floor"]["R"]["list"][f"R{i}"] = {
                "description": {
                    "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                    "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                },
                "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992702399418479/Frame_1062145930_2.png?ex=68e2540c&is=68e1028c&hm=7e9d5c189ee512af5111b907c8c1373e317904a7d325858af7187590981521cb&"
            }
        elif 44 < i < 71:
            seats["floor"]["Y"]["list"][f"Y{i}"] = {
                "description": {
                    "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                    "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                },
                "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992680488243290/Frame_1062145931_2.png?ex=68e25407&is=68e10287&hm=c027233f6ff9cad464d99056174bf25ecae606b7d9a21f0ea249877df52830be&"
            }
        elif 70 < i < 77:
            seats["floor"]["W"]["list"][f"W{i}"] = {
                "description": {
                    "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                    "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                },
                "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992659013402696/7869678_2.png?ex=68e25402&is=68e10282&hm=ed000ac0e181339c6dec13e624e305ffc3955c37b410ff22c88c61052df73f20&"
            }
        elif 76 < i < 86:
            seats["floor"]["Y"]["list"][f"Y{i}"] = {
                "description": {
                    "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                    "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                },
                "color": "ffc525",
                "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992680488243290/Frame_1062145931_2.png?ex=68e25407&is=68e10287&hm=c027233f6ff9cad464d99056174bf25ecae606b7d9a21f0ea249877df52830be&"
            }
        elif 85 < i < 108:
            seats["floor"]["P"]["list"][f"P{i}"] = {
                "description": {
                    "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                    "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                },
                "image": "https://cdn.discordapp.com/attachments/1365977478157303839/1423992627224903792/6789_2.png?ex=68e253fa&is=68e1027a&hm=448a7c040a1dea368993b2579064459d3cb45f59dc4a06dc8585283d3e958ffb&"
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

