import enum
import functools
import json
import sqlite3
import threading
from collections.abc import Callable
from contextlib import contextmanager

import discord

from data.extract_json import JsonExtract
from data.seat_data import SeatData, BookingStatus
from utils.logger import BotLogger

DATA_BASE = "data/tickets.db"

logger = BotLogger().get_file_logger(__name__)


def database_retry(max_retries: int = 3, delay: float = 0.1):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        last_exception = e
                        logger.warning(f"Database locked, retry {attempt + 1}/{max_retries}")

                        if attempt < max_retries - 1:
                            time.sleep(delay * (2 ** attempt))
                        continue
                    else:
                        raise e
                except Exception as e:
                    raise e

            logger.error(f"All retries failed for {func.__name__}")
            raise last_exception or sqlite3.OperationalError("Database locked after retries")

        return wrapper

    return decorator


class NotEmptySeatError(Exception):
    @classmethod
    def __str__(cls):
        return "Failed to finish off the object because its place is already taken"


class SeatStatus(enum.Enum):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'


class ThreadDatabase:
    def __init__(self, db_path: str, timeout: float = 30.0):
        self.db_path = db_path
        self.timeout = timeout
        self._local = threading.local()
        self._lock = threading.RLock()

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA busy_timeout=5000")
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    def close_connection(self):
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


class TicketBookingDatabase:
    def __init__(self):
        self.database = ThreadDatabase(DATA_BASE)

    @database_retry()
    def create_tables(self):
        with self.database.get_cursor() as cursor:
            for floor in JsonExtract.get_seats():
                cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS floor_{floor} (
                    seat TEXT UNIQUE, 
                    players TEXT,
                    status TEXT DEFAULT 'available'
                )
                ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS available_floors (
                    floor TEXT UNIQUE,
                    status TEXT DEFAULT 'available'
                )
                ''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS tickets ( 
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        ticket_number INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT DEFAULT 'open')''')

    @database_retry()
    def generate_seats(self):
        with self.database.get_cursor() as cursor:
            for floor in JsonExtract.get_seats():
                cursor.execute(
                    f'''SELECT players FROM floor_{floor};'''
                )
                cursor.execute(
                    f'''INSERT INTO available_floors (floor, status) VALUES (?, ?)''', (floor, SeatStatus.AVAILABLE.value)
                )
                if cursor.fetchone() is None:
                    data = SeatData(floor=floor)
                    for seat in data.get_seats():
                        cursor.execute(
                             f'''INSERT INTO floor_{floor} (seat, players) VALUES (?, ?)''', (seat, json.dumps({}))
                         )

    @database_retry()
    def get_seat_list(self, floor: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'''
                SELECT seat, players, status
                FROM floor_{floor}
            ''')
            return [(x[0], json.loads(x[1]), x[2]) for x in cursor.fetchall()]

    @database_retry()
    def get_seat(self, floor: str, seat: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'''SELECT seat, players, status FROM floor_{floor} WHERE seat = ?''', (seat,))
            info = cursor.fetchall()[0]
            return [info[0], json.loads(info[1]), info[2]]

    def all_users_count(self, floor: str) -> int:
        all_seats = self.get_seat_list(floor=floor)
        user_list = []
        for seat in all_seats:
            user_list.append(len(seat[1]))

        return sum(user_list)

    @database_retry()
    def add_user(self, floor: str, seat: str, players: dict, status: BookingStatus = None):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))

            players_dict = json.loads(cursor.fetchall()[0][0])

            players_dict[list(players.keys())[0]] = {"list": list(players.values())[0], "status": BookingStatus.CONFIRMED.value if status is None else status.value}
            cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (json.dumps(players_dict), seat))

    @database_retry()
    def remove_user(self, floor: str, seat: str, user_id: int):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            players_dict = json.loads(cursor.fetchall()[0][0])
            players_dict.pop(str(user_id))

            cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (json.dumps(players_dict), seat))

    @database_retry()
    def user_on_seat(self, floor: str, seat: str, user_id: int):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            players_dict = json.loads(cursor.fetchall()[0][0])

            return str(user_id) in players_dict.keys()

    @database_retry()
    def get_players_on_seat(self, floor: str, seat: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            players_dict = json.loads(cursor.fetchall()[0][0])

            all_values = [
                value["list"]
                for key, value in sorted(
                    players_dict.items(),
                    key=lambda x: x[0].lower() if x[0] else ""
                )
            ]
            return [item.strip() for sublist in all_values for item in sublist if item.strip()]

    @database_retry()
    def get_tickets_on_seat(self, floor: str, seat: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            players_dict = json.loads(cursor.fetchall()[0][0])

            all_values = [
                int(key)
                for key, value in sorted(
                    players_dict.items(),
                    key=lambda x: x[0].lower() if x[0] else ""
                )
            ]

            return all_values

    @database_retry()
    def set_seat_status(self, floor: str, seat: str, status: SeatStatus):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'UPDATE floor_{floor} SET status = ? WHERE seat = ?', (status.value, seat))

    @database_retry()
    def set_floor_status(self, floor: str, status: SeatStatus):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'UPDATE available_floors SET status = ? WHERE floor = ?', (status.value, floor))

    @database_retry()
    def set_booking_status(self, floor: str, seat: str, user_id: int, status: BookingStatus):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))

            players_dict = json.loads(cursor.fetchall()[0][0])

            players_dict[str(user_id)]["status"] = status.value
            cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (json.dumps(players_dict), seat))

    @database_retry()
    def seat_is_available(self, floor: str, seat: str):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT status FROM floor_{floor} WHERE seat = ?', (seat,))

            return cursor.fetchall()[0][0] == SeatStatus.AVAILABLE.value

    @database_retry()
    def floor_is_available(self, floor: str):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT status FROM available_floors WHERE floor = ?', (floor,))

            return cursor.fetchall()[0][0] == SeatStatus.AVAILABLE.value

    @database_retry()
    def user_in_seats(self, user: discord.User) -> bool:
        with self.database.get_cursor() as cursor:
            for floor in JsonExtract.get_seats():
                cursor.execute(f'''
                            SELECT seat, players, status
                            FROM floor_{floor}
                        ''')
                for seat in cursor.fetchall():
                    if str(user.id) in json.loads(seat[1]).keys():

                        return True
            return False

    def avalibles_seats(self, floor: str) -> tuple:
        all_seats = self.get_seat_list(floor=floor)
        availibles = []

        for seat in all_seats:
            if self.seat_is_available(floor=floor, seat=seat[0]):
                availibles.append(seat)

        return len(availibles), len(all_seats)


