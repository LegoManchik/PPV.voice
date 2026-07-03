import discord
from mutagen.mp3 import MP3

from typing import Optional

import config

FFMPEG_OPTIONS = {
    'options': '-vn -bufsize 8k -probesize 8k -analyzeduration 0 -fflags nobuffer -flags low_delay -loglevel quiet -hide_banner'
}


class AudioFile:
    def __init__(self, filename: str, player, source: Optional[discord.PCMVolumeTransformer] = None):
        if source is None:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS))

        self.song: dict = {
            'filename': filename,
            'source': source,
            'duration': self.get_duration(filename),
            'player': player
        }
        self.filename: str = filename
        self.source = self.song.get('source')
        self.volume: float = self.song.get('source').volume
        self.duration: int = self.song.get('duration')
        self.player = self.song.get('player')

    @staticmethod
    def get_duration(filename):
        try:
            if filename.endswith('.mp3'):
                from mutagen.mp3 import MP3
                audio = MP3(filename)
                return audio.info.length
        except:
            pass
        return 0
