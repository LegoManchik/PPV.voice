
import discord
import ffmpeg
from mutagen.mp3 import MP3


from discord_bot import config
from discord_bot.utils.ytdl_source import YTDLSource

FFMPEG_OPTIONS = {
    'before_options': '-re -fflags +genpts -flags low_delay -strict experimental',
    'options': '-vn -b:a 128k -filter:a "asetpts=N/SR/TB, volume=1.0" -af aresample=async=1',
}


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Сейчас играет:',
                               description='```\n{0.source.title}\n```'.format(self),
                               color=config.COLOR)
                 .add_field(name='Длительность', value=self.source.duration)
                 .add_field(name='Добавлено', value=self.requester.mention)
                 .add_field(name='Автор', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class AudioFile:
    __slots__ = ('song', 'source', 'filename', 'volume', 'duration', 'player')

    def __init__(self, filename: str, player):
        self.song: dict = {'filename': filename, 'source': discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS)), 'duration': self.get_duration(filename), 'player': player}
        self.filename: str = filename
        self.source = self.song.get('source')
        self.volume: float = self.song.get('source').volume
        self.duration: int = self.song.get('duration')
        self.player = self.song.get('player')

    def get_duration(self, filename):
        try:
            probe = ffmpeg.probe(filename)
            duration = round(float(probe['format']['duration']))
            return duration
        except:
            if filename.endswith('.mp3'):
                audio = MP3(filename)
                return audio.info.length
