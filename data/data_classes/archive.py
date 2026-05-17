from dataclasses import dataclass


@dataclass
class Archive:
    _last_track: str | None = None
    _track_list: list[str] = None

    def __post_init__(self):
        if self.track_list is None:
            self.track_list = []

    @property
    def last_track(self) -> str:
        return self._last_track

    @last_track.setter
    def last_track(self, value: str):
        self._last_track = value

    @property
    def track_list(self) -> list[str]:
        return self._track_list

    @track_list.setter
    def track_list(self, value: list[str]):
        self._track_list = value

    def add_track(self, value: str):
        self.last_track = value
        track_list = self._track_list
        track_list.append(value)
        self.track_list = track_list
