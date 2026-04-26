# Документация JSON-шаблона seats.json

---

### Параметр "mode"
Отпределяет вложенность мест.
```txt
A
├──1A
│  ├── 1 бронь
│  └── 2 бронь
├──2A
│  ├── 1 бронь
│  └── 2 бронь
└──3A
   ├── 1 бронь
   └── 2 бронь
```

| **Параметр** | **Описание**                                          |
|:---------|-------------------------------------------------------|
| `stadium`   | Место имеет возможность забронировать несколько билетов |
| `std` | Место имеет возможность забронировать 1 билет         |

Пример:

```json
{
  "mode": "stadium"
}
```

> Важно установить параметр `limit` в каждом месте

---
### Параметр "menu" (глобальное меню)
Используется на первом экране для выбора сектора.

| **Параметр**          | 	**Тип**    | 	**Описание                                   | 
|:--------------|---------|:----------------------------------------------|
| `title`       | 	`object` | 	Заголовок эмбеда. Ключи: en, ru              |
| `description` | 	`object` | 	Текст под заголовком. Ключи: en, ru          |
| `image`       | 	`object` | 	URL картинки-схемы всего зала. Ключи: en, ru |

Пример:

```json
{
  "menu": {
    "title": { 
      "en": "...", 
      "ru": "..."
    },
    "description": { 
      "en": "...", 
      "ru": "..."
    },
    "image": { 
      "en": "https://...", 
      "ru": "https://..."
    }
  }
}
```

---
### Параметр "floor"
Словарь секторов. Ключ → название кнопки сектора в Discord.

> Может быть любым: буквы, цифры, слова.

Пример:

```json
{
  "floor": {
    "A": {...},
    "B": {...},
    "1": {...},
    "$": {...}
  }
}
```
Ключ принимает следующие значения:
```json
{
  "A": {
    "menu": {...},
    "list": {
      "1A": {...},
      "2A": {...}
    }
  }
}
```
### Структура элемента "menu"
Отображается после выбора сектора.

| **Параметр**          | **Тип**   | 	**Описание**                                   |
|:--------------|-----------|-------------------------------------------------|
| `title`       | 	`object` | 	Заголовок эмбеда выбора мест                   |
| `description` | 	`object` | 	Описание сектора                               |
| `color`       | 	`string` | 	HEX-цвет (без #) → цвет полоски Discord эмбеда |
| `image`       | 	`string` | 	URL картинки-схемы этого сектора               |

Пример:

```json
{
  "A": {
    "menu": {
      "title": {
        "en": "A Sector",
        "ru": "A сектор"
      },
      "description": {
        "en": "...",
        "ru": "..."
      },
      "color": "fe8701",
      "image": "https://..."
    }
  }
}
```

### Структура элемента "list"

Пример:

```json
{
  "list": {
    "1A": {
      "description": {
        "en": "...",
        "ru": "..."
      },
      "image": "https://...",
      "color": "fe8701",
      "limit": 6
    }
  }
}

```
| **Параметр**        | 	**Тип**       | 	**Описание**                       |
|:------------|------------|-------------------------------------|
| `description` | 	`object`  | 	Текст в окне при выборе места      |
| `image`       | 	`string`  | 	URL миниатюры                      |
| `color`       | 	`string`  | 	HEX-цвет места                     |
| `limit`       | 	`number`  | 	Лимит билетов на одно место (seat) |

> Чтобы место *"не имело лимита"* нужно поставить значение параметра `limit: 9999`

---
### Пример полного JSON файла

```json
{
    "mode": "stadium",
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
            "en": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png",
            "ru": "https://media.discordapp.net/attachments/1365977478157303839/1446162623434326097/Base_Tickets.png"
        }
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
                "image": "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png"
            },
            "list": {
                "1A": {
                    "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    },
                    "color": "fe8701",
                    "image": "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png",
                    "limit": 6
                },
                "2A": {
                    "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    },
                    "color": "fe8701",
                    "image": "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png",
                    "limit": 6
                },
                "3A": {
                    "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    },
                    "color": "fe8701",
                    "image": "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png",
                    "limit": 3
                },
                "4A": {
                    "description": {
                        "en": "When booking tickets, you can specify up to three Minecraft Nicknames of you and your friends. Total number of seats per ticket: 3. In the nicknames window, specify the current MINECRAFT Nicknames of the players for whom this place is booked.",
                        "ru": "При бронировании билеты можно указать до трёх Minecraft-Ников вас и ваших друзей. Общее количество мест на 1 билет: 3. В окне никнеймов укажите актуальные MINECRAFT-Никнеймы игроков, на кого бронируется данное место."
                    },
                    "color": "fe8701",
                    "image": "https://media.discordapp.net/attachments/1365977478157303839/1446163630935638087/ee918978d36708aa.png",
                    "limit": 3
                }
            }
        }
    }
}

```
