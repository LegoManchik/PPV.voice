import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional


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
    """Менеджер плейлиста"""

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.tracks: List[PlaylistTrack] = []
        self.current_index = 0
        self._load_playlist()

    def _load_playlist(self):
        """Загрузить плейлист из JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.tracks = []
            for item in data:
                try:
                    self.tracks.append(PlaylistTrack(item))
                except Exception as e:
                    print(f"⚠️ Ошибка в треке {item.get('track', 'unknown')}: {e}")

            self.current_index = 0
            print(f"✅ Загружено {len(self.tracks)} треков из {self.json_path}")

        except FileNotFoundError:
            print(f"⚠️ Файл {self.json_path} не найден!")
            self.tracks = []
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            self.tracks = []

    def reload(self):
        """Перезагрузить плейлист"""
        self._load_playlist()
        self.current_index = 0

    def get_current_track(self) -> Optional[PlaylistTrack]:
        """Получить текущий трек"""
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    def get_next_track(self) -> Optional[PlaylistTrack]:
        """Получить следующий трек"""
        if self.current_index + 1 < len(self.tracks):
            return self.tracks[self.current_index + 1]
        return None

    def advance(self):
        """Перейти к следующему треку"""
        self.current_index += 1

    def reset(self):
        """Сбросить на начало"""
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

    def get_tracks_list(self, limit: int = 10) -> List[str]:
        result = []
        start = max(0, self.current_index - 2)
        end = min(len(self.tracks), start + limit)

        for i in range(start, end):
            track = self.tracks[i]
            name = track.filename
            marker = "▶️ " if i == self.current_index else f"{i + 1}. "
            delays = f" (start: {track.start_delay}s, end: {track.end_delay}s)"
            result.append(f"{marker}{name}{delays if i == self.current_index else ''}")

        return result