import os
import enum
import json
from dataclasses import dataclass


@dataclass
class Seat:
    _seat: str
    _players: dict[str]
    _status: bool

    @property
    def seat(self) -> str:
        return self._seat

    @seat.setter
    def seat(self, value: str):
        self._seat = value

    @property
    def players(self) -> dict[str]:
        return self._players

    @players.setter
    def players(self, value: dict[str]):
        self._players = value

    @property
    def status(self) -> bool:
        return self._status

    @status.setter
    def status(self, value: bool):
        self._status = value

