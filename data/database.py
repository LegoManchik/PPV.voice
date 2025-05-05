import sqlite3
from datetime import datetime

import discord
from discord.ext import commands
from discord.utils import get

import config
from data.seat_data import SeatData
from utils.localization import LangContext

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

        # Таблица для хранения тикетов
        self.cur.execute('''CREATE TABLE IF NOT EXISTS tickets ( 
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    ticket_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'open')''')

        # Таблица для счетчика тикетов
        self.cur.execute('''CREATE TABLE IF NOT EXISTS ticket_counter 
                     (guild_id INTEGER PRIMARY KEY,
                      last_number INTEGER DEFAULT 0)''')

        self.con.commit()

    async def get_next_ticket_number(self, guild_id: int) -> int:

        self.cur.execute('''INSERT OR IGNORE INTO ticket_counter (guild_id, last_number)
                     VALUES (?, 0)''', (guild_id,))
        self.cur.execute('''UPDATE ticket_counter 
                     SET last_number = last_number + 1 
                     WHERE guild_id = ?''', (guild_id,))
        self.cur.execute('''SELECT last_number FROM ticket_counter 
                     WHERE guild_id = ?''', (guild_id,))

        number = self.cur.fetchone()[0]
        self.con.commit()

        return number

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
            SELECT seat, user_id, players
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
