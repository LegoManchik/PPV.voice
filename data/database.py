import sqlite3

from data.seat_data import SeatData

DATA_BASE = "data/tickets.db"


class NotEmptySeatError(Exception):
    @classmethod
    def __str__(cls):
        return "Failed to finish off the object because its place is already taken"


class TicketBookingDatabase:
    def __init__(self):
        self.con = sqlite3.connect(DATA_BASE)
        self.cur = self.con.cursor()

    def __create_tables__(self):
        for i in range(1, 4):
            self.cur.execute(f'''
            CREATE TABLE IF NOT EXISTS floor_{i} (
                seat TEXT,
                user_id INTEGER,
                players TEXT
            )
            ''')
        self.con.commit()

    def generate_seats(self):
        for i in range(1, 4):
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
            SELECT seat, user_id
            FROM floor_{floor}
        ''')
        return self.cur.fetchall()

    def add_user(self, floor: int, seat: str, user_id: int, players: str):
        self.cur.execute(f'SELECT user_id FROM floor_{floor} WHERE seat = ?', (seat,))

        if self.cur.fetchall()[0][0] is None:
            self.cur.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (user_id, seat))
            self.cur.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (players, seat))
            self.con.commit()
        else:
            raise NotEmptySeatError()

    def remove_user(self, floor: int, seat: str):
        self.cur.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (None, seat))
        self.cur.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (None, seat))
        self.con.commit()
