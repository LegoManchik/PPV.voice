import asyncio
import io
import subprocess
import tempfile
from pathlib import Path, WindowsPath
from typing import Optional, Dict, Any, Coroutine
import discord
from discord import PCMVolumeTransformer, AudioSource
from discord.ext import commands

import config

from data.data_classes.audio_file import AudioFile, FFMPEG_OPTIONS
from data.data_classes.archive import Archive
from utils.logger import BotLogger
from utils.playlist import PlaylistManager, PlaylistTrack
from utils.sort_utils import first_number
from view.embed import BaseEmbeds

FFMPEG_INSTANT = {
    'options': '-vn -bufsize 8k -probesize 8k -analyzeduration 0 -fflags nobuffer -flags low_delay -loglevel quiet -hide_banner'
}

logger = BotLogger().get_file_logger(__name__)


class VoiceError(Exception):
    pass


class UltraFastAudioCache:

    def __init__(self, max_concurrent: int = 2):
        self._cache: Dict[str, bytes] = {}
        self._sources: Dict[str, discord.FFmpegPCMAudio] = {}
        self._source_cache: Dict[str, discord.PCMVolumeTransformer] = {}  # <-- ДОБАВЛЕНО
        self._preloading: Dict[str, asyncio.Future] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = None
        self._max_concurrent = max_concurrent
        self._ready = False

    def _decode_to_pcm_sync(self, file_path: str) -> Optional[bytes]:
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                'ffmpeg', '-i', file_path,
                '-ar', '48000',
                '-ac', '2',
                '-f', 'wav',
                '-y',
                '-loglevel', 'error',
                tmp_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            with open(tmp_path, 'rb') as f:
                pcm_data = f.read()

            try:
                Path(tmp_path).unlink()
            except:
                pass

            logger.debug(f"✅ Декодирован в PCM: {Path(file_path).name} ({len(pcm_data) / 1024:.1f} KB)")

            return pcm_data

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка FFmpeg при декодировании {file_path}: {e.stderr.decode() if e.stderr else str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования {file_path}: {e}")
            return None

    def _create_source_from_pcm(self, pcm_data: bytes) -> discord.FFmpegPCMAudio:
        return discord.FFmpegPCMAudio(
            io.BytesIO(pcm_data),
            pipe=True,
            **FFMPEG_INSTANT
        )

    def _get_executor(self):
        if self._executor is None:
            import concurrent.futures
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_concurrent
            )
        return self._executor

    async def preload(self, file_path: str) -> bool | None | Any:
        if file_path in self._sources:
            return True

        if file_path in self._cache:
            pcm_data = self._cache[file_path]
            self._sources[file_path] = self._create_source_from_pcm(pcm_data)
            return True

        if file_path in self._preloading:
            return await self._preloading[file_path]

        future = asyncio.Future()
        self._preloading[file_path] = future

        try:
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                pcm_data = await loop.run_in_executor(
                    self._get_executor(),
                    self._decode_to_pcm_sync,
                    file_path
                )

                if pcm_data:
                    self._cache[file_path] = pcm_data
                    self._sources[file_path] = self._create_source_from_pcm(pcm_data)
                    future.set_result(True)
                    logger.info(f"✅ Файл загружен в кэш: {Path(file_path).name}")
                    return True
                else:
                    future.set_result(False)
                    logger.warning(f"⚠️ Не удалось загрузить файл: {Path(file_path).name}")
                    return False

        except Exception as e:
            future.set_exception(e)
            logger.error(f"❌ Ошибка при предзагрузке {Path(file_path).name}: {e}")
            raise
        finally:
            await self._preloading.pop(file_path, None)

    async def preload_folder(self, folder_path: str):
        folder = Path(folder_path)
        if not folder.exists():
            logger.warning(f"⚠ Папка не найдена: {folder_path}")
            return

        files = list(folder.glob("*.mp3")) + list(folder.glob("*.wav")) + list(folder.glob("*.webm"))

        if not files:
            logger.warning(f"⚠ Нет аудиофайлов в папке: {folder_path}")
            return

        logger.info(f"🔄 Предзагрузка {len(files)} файлов из {folder_path}...")

        tasks = [self.preload(str(f)) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in results if r is True)
        self._ready = True

        logger.info(f"✅ Предзагружено {success}/{len(files)} файлов")

    def get_source(self, file_path: str) -> Optional[discord.PCMVolumeTransformer]:
        data = self._cache.get(file_path)

        if data is None:
            return None

        source = discord.FFmpegPCMAudio(
            io.BytesIO(data[:]),
            pipe=True,
            **FFMPEG_INSTANT
        )

        return discord.PCMVolumeTransformer(source)

    def is_preloaded(self, file_path: str) -> bool:
        return file_path in self._sources or file_path in self._cache

    def is_ready(self) -> bool:
        return self._ready

    def clear_cache(self):
        self._cache.clear()
        self._sources.clear()
        self._source_cache.clear()
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        self._ready = False

    def get_cache_stats(self) -> dict:
        total_mb = sum(len(v) for v in self._cache.values()) / (1024 * 1024)
        return {
            "files_in_memory": len(self._cache),
            "ready_sources": len(self._sources),
            "source_cache": len(self._source_cache),
            "total_memory_mb": round(total_mb, 2),
            "loading": len(self._preloading)
        }


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self.ctx = ctx
        self.TIMEOUT = 10800

        self.current = None
        self.voice = None
        self._volume = 1.0
        self._audio_cache = UltraFastAudioCache(max_concurrent=2)

        self.playlist_manager: Optional[PlaylistManager] = None
        self._is_playing_playlist = False
        self._is_playing_single = False

    @property
    def is_playing(self) -> bool:
        return self.voice and self.current and self.voice.is_playing()

    def is_connected(self) -> bool:
        return self.voice is not None and self.voice.is_connected()

    def load_playlist(self, json_path: str):
        self.playlist_manager = PlaylistManager(json_path)
        self._is_playing_playlist = False

        if self.playlist_manager and not self.playlist_manager.is_empty:
            logger.info(f"✅ Загружен плейлист: {Path(json_path).name} ({self.playlist_manager.total} треков)")
        else:
            logger.warning(f"⚠️ Плейлист пуст или не загружен: {json_path}")

    async def play_file(self, file: AudioFile, archive: Archive):
        if self._is_playing_playlist:
            self._is_playing_playlist = False
            if self.voice and self.voice.is_playing():
                self.voice.stop()

        if self.is_playing:
            self.ctx.menu_state.music_player.stop()
            self.skip()
            self.current = None

        track_name = Path(file.filename).stem
        archive.add_track(track_name)

        archive_embed = BaseEmbeds.processed_archive(
            self.ctx.menu_state.player.embeds[0],
            archive
        )
        await self.ctx.menu_state.player.edit(embeds=[archive_embed, self.ctx.menu_state.player.embeds[1]])

        await self._play_single_song(file, archive)

    async def _play_single_song(self, file: AudioFile, archive: Archive):
        if self.voice and self.voice.is_playing():
            self.voice.stop()

        source = self._audio_cache.get_source(file.filename)

        if source is None:
            await self._audio_cache.preload(file.filename)
            source = self._audio_cache.get_source(file.filename)

            if source is None:
                if self.ctx.menu_state and self.ctx.menu_state.player:
                    await self._show_status("❌ Ошибка загрузки")
                return

        file.source = source
        file.source.volume = self._volume

        self.current = file
        self._is_playing_single = True

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.start(self.current, self.current.player, archive)

        def after_playback(error):
            if error:
                logger.error(f"❌ Ошибка: {error}")

            self._is_playing_single = False
            asyncio.run_coroutine_threadsafe(
                self._on_single_song_end(archive),
                self.bot.loop
            )

        self.voice.play(self.current.source, after=after_playback)

    async def _on_single_song_end(self, archive: Archive):
        self._is_playing_single = False

        archive_embed = self.ctx.menu_state.player.embeds[0]
        await self.ctx.menu_state.player.edit(embeds=[archive_embed, BaseEmbeds.player()])
        self.current = None

    async def play_next_in_playlist(self, archive: Archive):
        if self._is_playing_single:
            if self.voice and self.voice.is_playing():
                self.voice.stop()
            self._is_playing_single = False

        if not self.playlist_manager or self.playlist_manager.is_empty:
            await self._stop_playback("📭 Плейлист пуст!")
            return

        if self.playlist_manager.current_index >= self.playlist_manager.total:
            self._is_playing_playlist = False
            await self._stop_playback("✅ Все треки воспроизведены!")
            return

        current = self.playlist_manager.get_current_track()
        if current is None:
            return

        if not Path(current.filepath).exists():
            logger.warning(f"⚠️ Файл не найден: {current.filepath}")
            self.playlist_manager.advance()
            await self.play_next_in_playlist(archive)
            return

        track_name = Path(current.filepath).stem
        archive.add_track(track_name)
        logger.info(f"▶️ Плейлист: воспроизведение {track_name} ({self.playlist_manager.current_index + 1}/{self.playlist_manager.total})")

        if self.ctx.menu_state and self.ctx.menu_state.player:
            archive_embed = BaseEmbeds.processed_archive(
                self.ctx.menu_state.player.embeds[0],
                archive
            )
            await self.ctx.menu_state.player.edit(embeds=[archive_embed, self.ctx.menu_state.player.embeds[1]])

        if current.start_delay > 0:
            await self._show_status(f"⏳ Задержка {current.start_delay} сек...")
            await asyncio.sleep(current.start_delay)

        file = AudioFile(current.filepath, self.ctx.menu_state.player)
        await self._play_playlist_song(file, archive, current)

    async def _play_playlist_song(self, file: AudioFile, archive: Archive, track: PlaylistTrack):
        if self.voice and self.voice.is_playing():
            self.voice.stop()

        self._is_playing_single = False
        self._is_playing_playlist = False
        self.current = None

        source = self._audio_cache.get_source(file.filename)

        if source is None:
            await self._show_status(f"🔄 Загрузка: {Path(file.filename).name}")
            await self._audio_cache.preload(file.filename)
            source = self._audio_cache.get_source(file.filename)

            if source is None:
                if self.ctx.menu_state and self.ctx.menu_state.player: \
                    await self._show_status(f"❌ Ошибка загрузки: {Path(file.filename).name}")

                self.playlist_manager.advance()
                await self.play_next_in_playlist(archive)
                return

        file.source = source
        file.source.volume = self._volume

        self.current = file
        self._is_playing_playlist = True

        if self.ctx.menu_state and self.ctx.menu_state.player:
            archive_embed = BaseEmbeds.processed_archive(
                self.ctx.menu_state.player.embeds[0],
                archive
            )
            await self.ctx.menu_state.player.edit(embeds=[archive_embed, self.ctx.menu_state.player.embeds[1]])

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.start(self.current, self.current.player, archive)

        def after_playback(error):
            if error:
                logger.error(f"❌ Ошибка воспроизведения в плейлисте: {error}")

            if self._is_playing_playlist and self.voice and not self.voice.is_playing():
                asyncio.run_coroutine_threadsafe(
                    self._on_playlist_song_end(archive, track),
                    self.bot.loop
                )

        self.voice.play(self.current.source, after=after_playback)

    async def _on_playlist_song_end(self, archive: Archive, track: PlaylistTrack):
        if not self._is_playing_playlist:
            return

        if self.voice and self.voice.is_playing():
            return

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.stop()

        if track.end_delay > 0:
            await self._show_status(f"⏳ Задержка {track.end_delay} сек...")
            await asyncio.sleep(track.end_delay)

        self.playlist_manager.advance()

        if self.playlist_manager.current_index >= self.playlist_manager.total:
            self._is_playing_playlist = False
            await self._stop_playback("✅ Все треки воспроизведены!")
            logger.info("✅ Плейлист завершён")
            return

        await self.play_next_in_playlist(archive)

    async def start_playlist(self, archive: Archive):
        if not self.playlist_manager or self.playlist_manager.is_empty:
            return

        if self._is_playing_single:
            if self.voice and self.voice.is_playing():
                self.voice.stop()
            self._is_playing_single = False

        self._is_playing_playlist = True
        self.playlist_manager.reset()
        await self.play_next_in_playlist(archive)

    def skip(self):
        if self.voice and self.voice.is_playing():
            self.voice.stop()

    async def _show_status(self, message: str):
        try:
            if self.ctx.menu_state and self.ctx.menu_state.player:
                archive_embed = self.ctx.menu_state.player.embeds[0]
                await self.ctx.menu_state.player.edit(embeds=[archive_embed, BaseEmbeds.player(message)])
            else:
                logger.warning("⚠ Не удалось обновить статус: player отсутствует")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")

    async def _stop_playback(self, message: str = "Воспроизведение остановлено"):
        self._is_playing_playlist = False
        self._is_playing_single = False

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.stop()

        try:
            if self.ctx.menu_state and self.ctx.menu_state.player:
                archive_embed = self.ctx.menu_state.player.embeds[0]
                await self.ctx.menu_state.player.edit(embeds=[archive_embed, BaseEmbeds.player()])
        except Exception as e:
            logger.error(f"❌ Ошибка остановки воспроизведения: {e}")

        self.current = None

    async def stop(self):
        if self.voice:
            self._is_playing_playlist = False
            self._is_playing_single = False
            self.voice.stop()
            await self.voice.disconnect()
            self.voice = None
            self.current = None

    async def reset_player(self):
        if self.voice and self.voice.is_playing():
            self.voice.stop()

        self._is_playing_playlist = False
        self._is_playing_single = False
        self.current = None

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.stop()

        if self.playlist_manager:
            self.playlist_manager.reset()

        logger.info("🔄 Плеер сброшен в исходное состояние")

    def clear_audio_cache(self):
        self._audio_cache.clear_cache()

    def get_cache_stats(self) -> dict:
        return self._audio_cache.get_cache_stats()


_global_cache = None


def get_global_cache() -> UltraFastAudioCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = UltraFastAudioCache(max_concurrent=2)

    return _global_cache


async def preload_folder_global(folder_path: str):
    cache = get_global_cache()
    await cache.preload_folder(folder_path)


async def preload_audio_global(file_path: str) -> bool:
    cache = get_global_cache()
    return await cache.preload(file_path)
