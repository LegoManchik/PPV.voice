import enum
import sqlite3

import discord

from data.seat_data import SeatData

DATA_BASE = "data/tickets.db"


class NotEmptySeatError(Exception):
    @classmethod
    def __str__(cls):
        return "Failed to finish off the object because its place is already taken"


class SeatStatus(enum.Enum):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'


class TicketBookingDatabase:
    def __init__(self):
        self.con = sqlite3.connect(DATA_BASE)
        self.cur = self.con.cursor()

    def __create_tables__(self):
        for i in range(1, 5):
            self.cur.execute(f'''
            CREATE TABLE IF NOT EXISTS floor_{i} (
                seat TEXT,
                user_id INTEGER,
                players TEXT,
                status TEXT DEFAULT 'available'
            )
            ''')

        self.cur.execute('''CREATE TABLE IF NOT EXISTS tickets ( 
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    ticket_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'open')''')

        self.con.commit()

    def generate_seats(self):
        for i in range(1, 5):
            self.cur.execute(
                f'''SELECT seat, user_id FROM floor_{i};'''
            )
            if self.cur.fetchone() is None:
                data = SeatData(floor=i)
                for j in data.get_seats():
                    self.cur.execute(
                        f'''INSERT INTO floor_{i} (seat, user_id) VALUES (?, ?)''', (j, None)
                    )
        self.con.commit()

    def get_seat_list(self, floor: int):
        self.cur.execute(f'''
            SELECT seat, user_id, players, status
            FROM floor_{floor}
        ''')
        return self.cur.fetchall()

    def add_user(self, floor: int, seat: str, user_id: int, players: str):
        self.cur.execute(f'SELECT user_id FROM floor_{floor} WHERE seat = ?', (seat,))

        if seat == "FanZone":
            self.cur.execute(
                f'''INSERT INTO floor_{floor} (seat, user_id, players, status) VALUES (?, ?, ?, ?)''', (seat, user_id, players, SeatStatus.UNAVAILABLE.value)
            )
            self.con.commit()
        else:
            if self.cur.fetchall()[0][0] is None:
                self.cur.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (user_id, seat))
                self.cur.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (players, seat))
                self.con.commit()
            else:
                raise NotEmptySeatError()

    def remove_user(self, floor: int, seat: str, user_id: int = None):
        if user_id is None:
            self.cur.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (None, seat))
            self.cur.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (None, seat))
        else:
            self.cur.execute(f'DELETE FROM floor_{floor} WHERE user_id = ?', (user_id,))
        self.con.commit()

    def set_seat_status(self, floor: int, seat: str, status: SeatStatus, user_id: int = None):
        if user_id is not None:
            self.cur.execute(f'UPDATE floor_{floor} SET status = ? WHERE user_id = ?', (status.value, user_id))
        else:
            self.cur.execute(f'UPDATE floor_{floor} SET status = ? WHERE seat = ?', (status.value, seat))
        self.con.commit()

    def is_avalible(self, floor: int, seat: str, user_id: int = None):
        if user_id is not None:
            self.cur.execute(f'SELECT status FROM floor_{floor} WHERE user_id = ?', (user_id,))
        else:
            self.cur.execute(f'SELECT status FROM floor_{floor} WHERE seat = ?', (seat,))
        self.con.commit()
        return self.cur.fetchall()[0][0] == SeatStatus.AVAILABLE.value

    def user_in_seats(self, user: discord.User):
        for floor in range(1, 4):
            self.cur.execute(f'''
                        SELECT seat, user_id, players, status
                        FROM floor_{floor}
                    ''')
            for seat in self.cur.fetchall():
                if user.id in seat:
                    return True
        return False
