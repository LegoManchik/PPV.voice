import discord
from mutagen.mp3 import MP3

import config

FFMPEG_OPTIONS = {
    'options': '-vn -bufsize 16k -probesize 16k -analyzeduration 0 -fflags nobuffer -flags low_delay'
}


class AudioFile:
    def __init__(self, filename: str, player):
        self.song: dict = {
            'filename': filename,
            'source': discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS)
            ),
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
        if filename.endswith('.mp3'):
            audio = MP3(filename)
            return audio.info.length
