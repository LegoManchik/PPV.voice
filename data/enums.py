import enum


class BookingStatus(enum.Enum):
    CONFIRMED = "confirmed"
    NOT_CONFIRMED = "not_confirmed"


class SeatModes(enum.Enum):
    STANDART = "std"  # max 1 ticket
    STADIUM = "stadium"  # 1++ tickets

    @classmethod
    def single_seats(cls):
        return [cls.STANDART.value]

    def get_modes(self):
        return self.__dict__
