import os
import enum
import functools
import json
import sqlite3
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager

import discord

import config
from config import DATABASE_PATH
from data.json_helper import JsonHelper
from data.data_classes.seat import Seat
from data.enums import BookingStatus
from utils.logger import BotLogger

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
                    if "database is locked" in str(e).lower():
                        last_exception = e
                        wait_time = delay * (2 ** attempt)
                        logger.warning(f"Database locked, retry {attempt + 1}/{max_retries} (waiting {wait_time:.2f}s)")
                        time.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception or sqlite3.OperationalError("Database locked after all retries")

        return wrapper

    return decorator


class SeatStatus(enum.Enum):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'

    @classmethod
    def to_bool(cls, value: str) -> bool:
        return value == cls.AVAILABLE.value

    @classmethod
    def from_bool(cls, value: bool) -> str:
        return cls.AVAILABLE.value if value else cls.UNAVAILABLE.value


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
            self._local.connection.execute("PRAGMA busy_timeout=30000")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.row_factory = sqlite3.Row
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
                logger.error(f"Database error, rolling back: {e}")
                raise
            finally:
                cursor.close()

    def close_connection(self):
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


class TicketBookingDatabase:
    def __init__(self):
        self.db = ThreadDatabase(DATABASE_PATH)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        try:
            self.create_tables()
            self.generate_seats()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @database_retry()
    def create_tables(self):
        with self.db.get_cursor() as cursor:
            for floor in JsonHelper.get_seats():
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS floor_{floor} (
                        seat TEXT PRIMARY KEY,
                        players TEXT DEFAULT '{{}}',
                        status TEXT DEFAULT 'available'
                    )
                ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS available_floors (
                    floor TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'available'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets ( 
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    ticket_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'open'
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)')

    @database_retry()
    def generate_seats(self):
        with self.db.get_cursor() as cursor:
            seats_data = JsonHelper.get_seats()

            for floor in seats_data:
                cursor.execute(
                    'INSERT OR IGNORE INTO available_floors (floor, status) VALUES (?, ?)',
                    (floor, SeatStatus.from_bool(True))
                )

                cursor.execute(f'SELECT seat FROM floor_{floor}')
                existing_seats = {row[0] for row in cursor.fetchall()}

                for seat in seats_data[floor]:
                    if seat not in existing_seats:
                        cursor.execute(
                            f'INSERT INTO floor_{floor} (seat, players) VALUES (?, ?)',
                            (seat, json.dumps({}))
                        )

    @database_retry()
    def get_seat_list(self, floor: str) -> list[Seat]:
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT seat, players, status FROM floor_{floor}')
            return [
                Seat(
                    row[0],
                    json.loads(row[1]),
                    SeatStatus.to_bool(row[2])
                )
                for row in cursor.fetchall()
            ]

    @database_retry()
    def get_seat(self, floor: str, seat: str) -> Seat:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f'SELECT seat, players, status FROM floor_{floor} WHERE seat = ?',
                (seat,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Seat {seat} not found on floor {floor}")

            return Seat(row[0], json.loads(row[1]), SeatStatus.to_bool(row[2]))

    @database_retry()
    def add_user(self, floor: str, seat: str, players: dict, status: BookingStatus = None):
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Seat {seat} not found")

            players_dict = json.loads(row[0])
            user_id = list(players.keys())[0]

            players_dict[user_id] = {
                "list": list(players.values())[0],
                "status": (status or BookingStatus.CONFIRMED).value
            }

            cursor.execute(
                f'UPDATE floor_{floor} SET players = ? WHERE seat = ?',
                (json.dumps(players_dict), seat)
            )

    @database_retry()
    def get_user_bookings_count(self, user_id: int) -> int:
        with self.db.get_cursor() as cursor:
            count = 0
            for floor in JsonHelper.get_seats():
                cursor.execute(f'SELECT players FROM floor_{floor}')
                rows = cursor.fetchall()
                for row in rows:
                    players_dict = json.loads(row[0])
                    if str(user_id) in players_dict:
                        count += 1
            return count

    @database_retry()
    def remove_user(self, floor: str, seat: str, user_id: int):
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            if not row:
                return

            players_dict = json.loads(row[0])
            players_dict.pop(str(user_id), None)

            cursor.execute(
                f'UPDATE floor_{floor} SET players = ? WHERE seat = ?',
                (json.dumps(players_dict), seat)
            )

    @database_retry()
    def user_on_seat(self, floor: str, seat: str, user_id: int) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            if not row:
                return False

            players_dict = json.loads(row[0])
            return str(user_id) in players_dict

    @database_retry()
    def get_players_on_seat(self, floor: str, seat: str) -> list[str]:
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            if not row:
                return []

            players_dict = json.loads(row[0])
            players_list = []
            for user_data in players_dict.values():
                players_list.extend(user_data.get("list", []))

            return [p.strip() for p in players_list if p.strip()]

    @database_retry()
    def get_tickets_on_seat(self, floor: str, seat: str) -> list[int]:
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            if not row:
                return []

            players_dict = json.loads(row[0])
            return [int(user_id) for user_id in players_dict.keys()]

    @database_retry()
    def set_seat_status(self, floor: str, seat: str, status: bool):
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f'UPDATE floor_{floor} SET status = ? WHERE seat = ?',
                (SeatStatus.from_bool(status), seat)
            )

    @database_retry()
    def set_floor_status(self, floor: str, status: bool):
        with self.db.get_cursor() as cursor:
            cursor.execute(
                'UPDATE available_floors SET status = ? WHERE floor = ?',
                (SeatStatus.from_bool(status), floor)
            )

    @database_retry()
    def set_booking_status(self, floor: str, seat: str, user_id: int, status: BookingStatus):
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT players FROM floor_{floor} WHERE seat = ?', (seat,))

            players_dict = json.loads(cursor.fetchall()[0][0])

            players_dict[str(user_id)]["status"] = status.value
            cursor.execute(f'UPDATE floor_{floor} SET players = ? WHERE seat = ?', (json.dumps(players_dict), seat))

    @database_retry()
    def seat_is_available(self, floor: str, seat: str) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute(f'SELECT status FROM floor_{floor} WHERE seat = ?', (seat,))
            row = cursor.fetchone()
            return row and row[0] == SeatStatus.AVAILABLE.value

    @database_retry()
    def floor_is_available(self, floor: str) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute('SELECT status FROM available_floors WHERE floor = ?', (floor,))
            row = cursor.fetchone()
            return row and row[0] == SeatStatus.AVAILABLE.value

    def all_users_count(self, floor: str) -> int:
        seats = self.get_seat_list(floor)
        return sum(len(seat.players) for seat in seats)

    def availables_seats(self, floor: str) -> tuple[int, int]:
        seats = self.get_seat_list(floor)
        available_count = sum(1 for seat in seats if seat.status)
        return available_count, len(seats)

    @database_retry()
    def user_in_seats(self, user: discord.User) -> bool:
        with self.db.get_cursor() as cursor:
            for floor in JsonHelper.get_seats():
                cursor.execute(f'SELECT players FROM floor_{floor}')
                for row in cursor.fetchall():
                    players_dict = json.loads(row[0])
                    if str(user.id) in players_dict:
                        return True
            return False

    @database_retry()
    def get_ticket_by_channel(self, channel_id: int) -> dict | None:
        with self.db.get_cursor() as cursor:
            cursor.execute('''SELECT id, user_id, channel_id, ticket_number, created_at, status 
                             FROM tickets WHERE channel_id = ?''', (channel_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return {
                'id': row[0],
                'user_id': row[1],
                'channel_id': row[2],
                'ticket_number': row[3],
                'created_at': row[4],
                'status': row[5]
            }

    @database_retry()
    def get_ticket_by_user(self, user_id: int, status: str = None) -> list:
        with self.db.get_cursor() as cursor:
            if status:
                cursor.execute('''SELECT id, user_id, channel_id, ticket_number, created_at, status 
                                 FROM tickets WHERE user_id = ? AND status = ?''', (user_id, status))
            else:
                cursor.execute('''SELECT id, user_id, channel_id, ticket_number, created_at, status 
                                 FROM tickets WHERE user_id = ?''', (user_id,))

            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'channel_id': row[2],
                    'ticket_number': row[3],
                    'created_at': row[4],
                    'status': row[5]
                }
                for row in rows
            ]

    @database_retry()
    def get_all_tickets(self, status: str = None, limit: int = 100, offset: int = 0) -> list:
        with self.db.get_cursor() as cursor:
            if status:
                cursor.execute('''SELECT id, user_id, channel_id, ticket_number, created_at, status 
                                 FROM tickets WHERE status = ? 
                                 ORDER BY created_at DESC LIMIT ? OFFSET ?''', (status, limit, offset))
            else:
                cursor.execute('''SELECT id, user_id, channel_id, ticket_number, created_at, status 
                                 FROM tickets ORDER BY created_at DESC LIMIT ? OFFSET ?''', (limit, offset))

            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'channel_id': row[2],
                    'ticket_number': row[3],
                    'created_at': row[4],
                    'status': row[5]
                }
                for row in rows
            ]

    @database_retry()
    def get_ticket_stats(self) -> dict:
        with self.db.get_cursor() as cursor:
            cursor.execute('''SELECT 
                             COUNT(*) as total,
                             SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open,
                             SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed
                             FROM tickets''')
            row = cursor.fetchone()

            return {
                'total': row[0],
                'open': row[1],
                'closed': row[2]
            }

    @database_retry()
    def delete_ticket(self, ticket_id: int) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
            return cursor.rowcount > 0

    @database_retry()
    def update_ticket_status(self, channel_id: int, status: str) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute('UPDATE tickets SET status = ? WHERE channel_id = ?', (status, channel_id))
            return cursor.rowcount > 0

    def close_all_connections(self):
        self.db.close_connection()
