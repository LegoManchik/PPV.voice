import enum
import functools
import sqlite3
import threading
from collections.abc import Callable
from contextlib import contextmanager

import discord

from discord_bot.data.extract_json import JsonExtract
from discord_bot.data.seat_data import SeatData
from discord_bot.utils.logger import BotLogger

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
            for i in JsonExtract.get_seats():
                cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS floor_{i} (
                    seat TEXT,
                    user_id INTEGER,
                    players TEXT,
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
                    f'''SELECT seat, user_id FROM floor_{floor};'''
                )
                if cursor.fetchone() is None:
                    data = SeatData(floor=floor)
                    for seat in data.get_seats():
                        cursor.execute(
                             f'''INSERT INTO floor_{floor} (seat, user_id) VALUES (?, ?)''', (seat, None)
                         )

    @database_retry()
    def get_seat_list(self, floor: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'''
                SELECT seat, user_id, players, status
                FROM floor_{floor}
            ''')
            return cursor.fetchall()

    @database_retry()
    def get_seat(self, floor: str, seat: str) -> list:
        with self.database.get_cursor() as cursor:
            cursor.execute(f'''
                SELECT seat, user_id, players, status
                FROM floor_{floor} WHERE seat = ?
            ''', (seat,))
            return cursor.fetchall()

    @database_retry()
    def add_user(self, floor: str, seat: str, user_id: int, players: str):
        with self.database.get_cursor() as cursor:
            cursor.execute(f'SELECT user_id FROM floor_{floor} WHERE seat = ?', (seat,))

            if cursor.fetchall()[0][0] is None:
                cursor.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (user_id, seat))
                cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (players, seat))
            else:
                raise NotEmptySeatError()

    @database_retry()
    def remove_user(self, floor: str, seat: str, user_id: int = None):
        with self.database.get_cursor() as cursor:
            if user_id is None:
                cursor.execute(f'UPDATE floor_{floor} SET user_id = ? WHERE seat = ?', (None, seat))
                cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (None, seat))
            else:
                cursor.execute(f'DELETE FROM floor_{floor} WHERE user_id = ?', (user_id,))

    @database_retry()
    def set_seat_status(self, floor: str, seat: str, status: SeatStatus, user_id: int = None):
        with self.database.get_cursor() as cursor:
            if user_id is not None:
                cursor.execute(f'UPDATE floor_{floor} SET status = ? WHERE user_id = ?', (status.value, user_id))
            else:
                cursor.execute(f'UPDATE floor_{floor} SET status = ? WHERE seat = ?', (status.value, seat))

    @database_retry()
    def is_avalible(self, floor: str, seat: str, user_id: int = None):
        with self.database.get_cursor() as cursor:
            if user_id is not None:
                cursor.execute(f'SELECT status FROM floor_{floor} WHERE user_id = ?', (user_id,))
            else:
                cursor.execute(f'SELECT status FROM floor_{floor} WHERE seat = ?', (seat,))

            return cursor.fetchall()[0][0] == SeatStatus.AVAILABLE.value

    @database_retry()
    def user_in_seats(self, user: discord.User) -> bool:
        with self.database.get_cursor() as cursor:
            for floor in JsonExtract.get_seats():
                cursor.execute(f'''
                            SELECT seat, user_id, players, status
                            FROM floor_{floor}
                        ''')
                for seat in cursor.fetchall():
                    if user.id in seat:
                        return True
            return False

    def avalibles_seats(self, floor: str) -> tuple:
        all_seats = self.get_seat_list(floor=floor)
        availibles = []

        for seat in all_seats:
            if self.is_avalible(floor=floor, seat=seat[0]):
                availibles.append(seat)

        return len(availibles), len(all_seats)
