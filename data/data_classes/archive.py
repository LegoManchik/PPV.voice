from dataclasses import dataclass

import discord

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


class PlayerEmbedHelper:
    @staticmethod
    def create_archive_embed(embed: discord.Embed, archive: Archive, last_track: str = None) -> discord.Embed:
        embed.clear_fields()

        if last_track is not None:
            archive.add_track(last_track)

        track_list = archive.track_list
        if len(track_list) > 6:
            embed.add_field(name=f"И ещё ({len(track_list) - 6}) треков...", value="", inline=False)

        for track in track_list[-6:][:-1]:
            embed.add_field(name="", value=f"`{track}`", inline=False)

        embed.add_field(name="Последний трек:", value=f"`{archive.last_track}`", inline=False)

        return embed