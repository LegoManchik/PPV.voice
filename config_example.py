import os
BOT_VERSION = "1.0"  # Версия бота. НЕ ТРОГАТЬ!!!

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data/tickets.db")              # Пути к файлам.
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "data/templates/seats.json")    # Менять не рекомендуется

PREFIX = """<Вставить значение>"""  # Префикс команд

COLOR = """<Вставить значение>"""  # HEX-код цвета 0x<HEX-код>

GUILD_ID = """<Вставить значение>"""  # ID сервера

OPERATOR_ROLE_ID = """<Вставить значение>"""  # Роль для управления ботом
SUPERVISOR_ROLE_ID = """<Вставить значение>"""  # Роль супервайзера (для управления ботом)

EN_ROLE_ID = """<Вставить значение>"""  # ID Языковых ролей
RU_ROLE_ID = """<Вставить значение>"""  #

NONE_ROLE_ID = """<Вставить значение>"""  # Декоративная роль None (для UI)

TICKETS_CATEGORY_ID = """<Вставить значение>"""  # Категория для тикетов

CONFIRMATION_CHANNEL_ID = """<Вставить значение>"""  # Канал для подтверждения бронирования


