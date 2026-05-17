import asyncio

from discord.ext import commands
from data.data_classes.audio_file import AudioFile
from data.data_classes.archive import Archive


class VoiceError(Exception):
    pass


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self.ctx = ctx

        self.TIMEOUT = 10800

        self.current = None
        self.voice = None
        self._volume = 1.0

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current
    
    async def play_file(self, file: AudioFile, archive: Archive):
        if self.is_playing:
            self.ctx.menu_state.music_player.stop()
            self.skip()
            self.current = None
            
        self.current = file
        self.ctx.menu_state.music_player.start(self.current, self.current.player, archive)
        self.voice.play(self.current.source)
        self.voice.source.volume = self._volume

    def skip(self):
        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        if self.voice:
            await self.voice.disconnect()
            self.voice = None
