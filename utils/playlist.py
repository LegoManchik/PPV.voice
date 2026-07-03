import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.logger import BotLogger

logger = BotLogger().get_file_logger(__name__)


class PlaylistTrack:
    def __init__(self, data: Dict[str, Any]):
        self.start_delay = data.get("start_delay", 0)
        self.track = data.get("track", "")
        self.end_delay = data.get("end_delay", 0)
        self._validate()

    def _validate(self):
        if not self.track:
            raise ValueError("Track path is empty")
        if not Path(self.track).exists():
            raise FileNotFoundError(f"Track file not found: {self.track}")

    @property
    def filename(self) -> str:
        return Path(self.track).name

    @property
    def filepath(self) -> str:
        return self.track

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_delay": self.start_delay,
            "track": self.track,
            "end_delay": self.end_delay
        }


class PlaylistManager:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.tracks: List[PlaylistTrack] = []
        self.current_index = 0
        self._load_playlist()

    def _load_playlist(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.tracks = []
            for item in data:
                try:
                    self.tracks.append(PlaylistTrack(item))
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка в треке {item.get('track', 'unknown')}: {e}")

            self.current_index = 0

        except FileNotFoundError:
            logger.warning(f"⚠️ Файл {self.json_path} не найден!")
            self.tracks = []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            self.tracks = []

    def reload(self):
        self._load_playlist()
        self.current_index = 0

    def get_current_track(self) -> Optional[PlaylistTrack]:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    def get_next_track(self) -> Optional[PlaylistTrack]:
        if self.current_index + 1 < len(self.tracks):
            return self.tracks[self.current_index + 1]
        return None

    def advance(self):
        self.current_index += 1

    def reset(self):
        self.current_index = 0

    @property
    def is_empty(self) -> bool:
        return len(self.tracks) == 0

    @property
    def total(self) -> int:
        return len(self.tracks)

    @property
    def remaining(self) -> int:
        return len(self.tracks) - self.current_index

    @property
    def current_track_name(self) -> str:
        track = self.get_current_track()
        return track.filename if track else "None"
