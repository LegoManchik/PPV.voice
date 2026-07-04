import json
from utils.logger import BotLogger
from config import TEMPLATE_PATH

logger = BotLogger().get_file_logger(__name__)

MODE_VALUES = ["std", "stadium"]
LANG_KEYS = ["en", "ru"]
DEFAULT_BOOKING_LIMIT = 1


class LostModeError(Exception):
    @classmethod
    def __str__(cls):
        return "Отсутствует параметр `mode`"


class LostGlobalMenuError(Exception):
    @classmethod
    def __str__(cls):
        return "Отсутствует параметр `menu`"


class LostFloorError(Exception):
    @classmethod
    def __str__(cls):
        return "Отсутствует параметр `floor`"


class LostMenuError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `menu` По пути: `{self.path}`"


class LostTitleError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `title` По пути: `{self.path}`"


class LostDescriptionError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `description` По пути: `{self.path}`"


class LostImageError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `image` По пути: `{self.path}`"


class LostColorError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `color` По пути: `{self.path}`"


class LostLimitError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `limit` По пути: `{self.path}`"


class LostLangKeyError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Отсуствует параметр `{self.path}`"


class NoFloorsError(Exception):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Пустой список секторов `{self.path}`"


class NonExistentArgumentError(Exception):
    def __init__(self, path: str, arg: str):
        self.path = path
        self.arg = arg

    def __str__(self):
        return f"Не подходящий аргумент: `{self.arg}`, по пути: `{self.path}`"


class LostBookingLimitError(Exception):
    @classmethod
    def __str__(cls):
        return "Отсутствует параметр `booking_limit`"


class InvalidBookingLimitError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"Некорректное значение `booking_limit`: {self.value}. Ожидается целое положительное число"


class SeatsDebug:
    @classmethod
    async def test(cls):
        logger.info("🔄 Проверка целостности `seats.json`...")

        errors = []

        cls.check_mode(errors)
        cls.check_booking_limit(errors)
        cls.check_global_menu(errors)
        cls.check_floor(errors)

        if errors:
            logger.error(f"Найдено {len(errors)} ошибок:")
            for error in errors:
                logger.error(f"  • {error}")
            logger.warning("⚠ Наличие этих ошибок может привести к не правильному отображению элементов, или не правильной работе бота")

        else:
            logger.info("✅ Проверка успешно закончена!")

    @classmethod
    def check_lang_keys(cls, _dict: dict, path: str, errors: list):
        for key in LANG_KEYS:
            if _dict.get(key) is None:
                errors.append(str(LostLangKeyError(f"{path}.{key}")))

    @classmethod
    def check_mode(cls, errors: list):
        try:
            with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
                mode = json.load(file).get("mode")
                if mode is None:
                    errors.append(str(LostModeError()))
                if mode not in MODE_VALUES:
                    errors.append(str(NonExistentArgumentError("mode", mode)))
        except Exception as e:
            errors.append(f"❌ Ошибка при проверке mode: {e}")

    @classmethod
    def check_booking_limit(cls, errors: list):
        try:
            with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
                data = json.load(file)
                booking_limit = data.get("booking_limit")

                if booking_limit is None:
                    data["booking_limit"] = DEFAULT_BOOKING_LIMIT
                    file.seek(0)
                    json.dump(data, file, ensure_ascii=False, indent=4)
                    file.truncate()
                    logger.info(
                        f"✅ Параметр `booking_limit` отсутствовал, установлено значение по умолчанию: {DEFAULT_BOOKING_LIMIT}")
                else:
                    try:
                        limit = int(booking_limit)
                        if limit < 0:
                            errors.append(str(InvalidBookingLimitError(booking_limit)))

                            data["booking_limit"] = DEFAULT_BOOKING_LIMIT
                            file.seek(0)
                            json.dump(data, file, ensure_ascii=False, indent=4)
                            file.truncate()
                            logger.warning(
                                f"⚠️ Отрицательное значение `booking_limit` исправлено на {DEFAULT_BOOKING_LIMIT}")
                        elif limit == 0:
                            logger.info("ℹ️ `booking_limit` установлен в 0 - бронирование запрещено для всех")
                    except ValueError:
                        errors.append(str(InvalidBookingLimitError(booking_limit)))

                        data["booking_limit"] = DEFAULT_BOOKING_LIMIT
                        file.seek(0)
                        json.dump(data, file, ensure_ascii=False, indent=4)
                        file.truncate()
                        logger.warning(
                            f"⚠️ Некорректное значение `booking_limit` исправлено на {DEFAULT_BOOKING_LIMIT}")

        except Exception as e:
            errors.append(f"❌ Ошибка при проверке booking_limit: {e}")

    @classmethod
    def check_global_menu(cls, errors: list):
        try:
            with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
                data = json.load(file)
                menu = data.get("menu")

            if menu is None:
                errors.append(str(LostGlobalMenuError()))
                return

            title = menu.get("title")
            description = menu.get("description")
            image = menu.get("image")

            if title is None:
                errors.append(str(LostTitleError("menu")))
            else:
                cls.check_lang_keys(title, "menu.title", errors)

            if description is None:
                errors.append(str(LostDescriptionError("menu")))
            else:
                cls.check_lang_keys(description, "menu.description", errors)

            if image is None:
                errors.append(str(LostImageError("menu")))
            else:
                cls.check_lang_keys(image, "menu.image", errors)

        except Exception as e:
            errors.append(f"❌ Ошибка при проверке global_menu: {e}")

    @classmethod
    def check_floor(cls, errors: list):
        try:
            with open(TEMPLATE_PATH, "r+", encoding="utf-8") as file:
                data = json.load(file)
                floor = data.get("floor")

            if floor is None:
                errors.append(str(LostFloorError()))
                return

            if len(list(floor.keys())) < 1:
                errors.append(str(NoFloorsError("floor")))

            for key, value in floor.items():
                menu = value.get("menu")

                if menu is None:
                    errors.append(str(LostMenuError(f"{key}")))
                    continue

                description = menu.get("description")
                color = menu.get("color")
                image = menu.get("image")

                if description is None:
                    errors.append(str(LostDescriptionError(f"{key}.menu.description")))
                else:
                    cls.check_lang_keys(description, f"{key}.menu.description", errors)

                if color is None:
                    errors.append(str(LostColorError(f"{key}.menu.color")))

                if image is None:
                    errors.append(str(LostImageError(f"{key}.menu.image")))
                    continue

                _list = value.get("list")
                if _list is None:
                    errors.append(str(LostMenuError(f"{key}.list")))
                    continue

                for list_key, list_value in _list.items():
                    seat_description = list_value.get("description")
                    seat_color = list_value.get("color")
                    seat_image = list_value.get("image")
                    seat_limit = list_value.get("limit")

                    if seat_description is None:
                        errors.append(str(LostDescriptionError(f"{key}.{list_key}.description")))
                    else:
                        cls.check_lang_keys(seat_description, f"{key}.{list_key}.description", errors)

                    if seat_color is None:
                        errors.append(str(LostColorError(f"{key}.{list_key}.color")))

                    if seat_image is None:
                        errors.append(str(LostImageError(f"{key}.{list_key}.image")))

                    if seat_limit is None or seat_limit < 0:
                        errors.append(str(LostLimitError(f"{key}.{list_key}.limit")))

        except Exception as e:
            errors.append(f"❌ Ошибка при проверке floor: {e}")


if __name__ == "__main__":
    SeatsDebug.test()
