import asyncio

import discord
import yt_dlp

from urllib.request import urlopen
from urllib.error import HTTPError

from yt_dlp.compat import functools

yt_dlp.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': 'audio_files/%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'options': '-vn -filter:a "volume=1.0"',
    }

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, inter: discord.Interaction, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = inter.author
        self.channel = inter.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, inter: discord.Interaction, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=True)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        
        try:
            urlopen(info['url'])
        except HTTPError as e:
            if e.code == 403:
                filename = yt_dlp.YoutubeDL(cls.YTDL_OPTIONS).prepare_filename(info)
                
                return cls(inter, discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **cls.FFMPEG_OPTIONS)), data=info) 
        else:
            return cls(inter, discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS)), data=info)
        
    @classmethod
    def download(cls, url: str, folder: str = 'audio_files'):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'audio_files/{folder}/%(id)s.%(ext)s',
        }   
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        info_dict = ydl.extract_info(url, download=True)
        downloaded_file_path = ydl.prepare_filename(info_dict)

        return downloaded_file_path
    
    @classmethod
    async def file_source(cls, inter, filename: str):

        return cls(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **cls.FFMPEG_OPTIONS)))
        
    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        duration = []
        if days > 0:
            duration.append(f'{days} дн.')
        if hours > 0:
            duration.append(f'{hours} час.')
        if minutes > 0:
            duration.append(f'{minutes} мин.')
        if seconds > 0:
            duration.append(f'{seconds} сек.')

        return ' '.join(duration)
