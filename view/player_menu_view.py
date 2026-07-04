import asyncio
import datetime
import os
import traceback
import json

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import discord
from discord import ui, SelectOption
from discord.ext import commands

import config
from data.data_classes.audio_file import AudioFile
from data.data_classes.archive import Archive
from utils.logger import interaction_error_handler, BotLogger
from utils.voice_utils import VoiceState
from view.embed import BaseEmbeds
from view.emojis import ButtonIcons

logger = BotLogger().get_file_logger(__name__)


class PlayerState(Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


class ButtonAction(Enum):
    VOLUME_DOWN = "volume-"
    VOLUME_UP = "volume+"
    VOLUME_QUIET = "quiet"
    VOLUME_10 = "volume_10"
    VOLUME_50 = "volume_50"
    VOLUME_100 = "volume_100"
    STOP = "stop_button"
    PAUSE = "pause_button"
    RESUME = "resume_button"


VOLUME_PRESETS = {
    ButtonAction.VOLUME_QUIET: 0,
    ButtonAction.VOLUME_10: 0.1,
    ButtonAction.VOLUME_50: 0.5,
    ButtonAction.VOLUME_100: 1.0
}


class PlayerContext:
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.archive: Optional['Archive'] = None
        self.player: Optional['MusicPlayer'] = None
        self.menu: Optional[discord.Message] = None

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        self.player = None
        self.menu = None
        self.archive = None


class MusicPlayer:
    def __init__(self, ctx: commands.Context, components: List[Dict[str, Any]]):
        self.ctx = ctx
        self.components = components

        self._counter_task: Optional[asyncio.Task] = None
        self._state: PlayerState = PlayerState.STOPPED
        self._start_time: Optional[datetime.datetime] = None
        self._elapsed_time: float = 0
        self._current_song: Optional[AudioFile] = None

    @property
    def is_playing(self) -> bool:
        return self._state == PlayerState.PLAYING and self.ctx.voice_state.is_playing

    @property
    def is_paused(self) -> bool:
        return self._state == PlayerState.PAUSED and self.ctx.voice_state.voice.is_paused()

    async def start_counter(self, song: AudioFile, player_message: discord.Message, archive: Archive):
        archive_embed = BaseEmbeds.processed_archive(
            self.ctx.menu_state.player.embeds[0], archive
        )

        player_embed = self.ctx.menu_state.player.embeds[1]
        song_name = os.path.splitext(os.path.basename(song.filename))[0]
        player_embed.description = f'```{song_name}```'

        bar_length = 20

        while self._elapsed_time < song.duration and self._state != PlayerState.STOPPED:
            if self._state == PlayerState.PLAYING:
                current_time = discord.utils.utcnow()
                self._elapsed_time = (current_time - self._start_time).total_seconds()

                progress_percent = self._elapsed_time / song.duration
                progress_percent = min(max(progress_percent, 0), 1)

                filled_length = int(bar_length * progress_percent)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)

                current_time_str = self._format_time(self._elapsed_time)
                total_time_str = self._format_time(song.duration)

                footer_text = f'{current_time_str} / {total_time_str} {bar}'
                player_embed.set_footer(text=footer_text)

                await player_message.edit(embeds=[archive_embed, player_embed])

            await asyncio.sleep(0.5)

        if self._state != PlayerState.STOPPED:
            await self._stop_playback(player_message)

    async def _stop_playback(self, message: discord.Message):
        archive_embed = self.ctx.menu_state.player.embeds[0]
        await message.edit(embeds=[archive_embed, BaseEmbeds.player()])
        self.stop()

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = round(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        return f"{minutes:02}:{seconds:02}"

    def start(self, song: AudioFile, player_message: discord.Message, archive: Archive):
        if self._counter_task:
            self._counter_task.cancel()
            self._counter_task = None

        self._current_song = song
        self._state = PlayerState.PLAYING
        self._start_time = discord.utils.utcnow()
        self._elapsed_time = 0

        self._counter_task = asyncio.create_task(
            self.start_counter(song, player_message, archive)
        )

    def pause(self):
        if self._state == PlayerState.PLAYING:
            self._state = PlayerState.PAUSED
            self._elapsed_time = (discord.utils.utcnow() - self._start_time).total_seconds()

    def resume(self):
        if self._state == PlayerState.PAUSED:
            self._state = PlayerState.PLAYING
            self._start_time = discord.utils.utcnow() - datetime.timedelta(seconds=self._elapsed_time)

    def stop(self):
        if self._counter_task:
            self._counter_task.cancel()
            self._counter_task = None

        self._state = PlayerState.STOPPED
        self._elapsed_time = 0
        self._start_time = None
        self._current_song = None


class ControlButtons(ui.View):
    def __init__(self, ctx: commands.Context, player: MusicPlayer):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player
        self._setup_buttons()
        ctx.bot.add_view(self)

    def _setup_buttons(self):
        self.clear_items()

        for data in self.player.components:
            button = discord.ui.Button(
                label=data['label'],
                style=data['style'],
                custom_id=data['custom_id']
            )
            button.callback = self._create_button_callback(data['custom_id'])
            self.add_item(button)

    def _create_button_callback(self, custom_id: str):
        async def callback(inter: discord.Interaction):
            if inter and not inter.response.is_done():
                await inter.response.defer(ephemeral=True)

            await self._handle_file_playback(inter, custom_id)

        return callback

    async def _handle_file_playback(self, inter: discord.Interaction, file_path: str):
        await _ensure_voice_connection(self.ctx, inter)

        voice_state = self.ctx.voice_state

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.stop()

        if voice_state.is_playing:
            voice_state.voice.stop()

        voice_state._is_playing_playlist = False
        voice_state._is_playing_single = False
        voice_state.current = None

        self.player.stop()

        if self._is_audio_file(file_path):
            cached_source = self.ctx.voice_state._audio_cache.get_source(file_path)

            if cached_source:
                file = AudioFile(file_path, self.ctx.menu_state.player, source=cached_source)
            else:
                file = AudioFile(file_path, self.ctx.menu_state.player)

            await self.ctx.voice_state.play_file(file, self.ctx.menu_state.archive)

            volume = self.ctx.voice_state.volume if self.ctx.voice_state else 1.0
            await self._update_to_control_view(inter, volume)

    @staticmethod
    def _is_audio_file(file_path: str) -> bool:
        return any(file_path.endswith(ext) for ext in ('.webm', '.mp3', '.wav'))

    async def _update_to_control_view(self, inter: discord.Interaction, volume: float):
        await self.ctx.menu_state.menu.edit(
            view=MusicControlView(self.ctx, self.player, volume)
        )


class MusicControlView(ui.LayoutView):
    def __init__(self, ctx: commands.Context, player: MusicPlayer, volume: float = None):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player
        self._volume = volume or 1.0

        self.container = ui.Container(accent_color=config.COLOR)

        self._setup_buttons()
        ctx.bot.add_view(self)

    def _setup_buttons(self):
        self._add_volume_buttons()
        self._add_preset_buttons()
        self._add_playback_buttons()
        self._add_playlist_buttons()
        self.add_item(self.container)

    def _add_playlist_buttons(self):

        play_all_btn = ui.Button(
            emoji=ButtonIcons.RESUME.value,
            label="Воспроизвести все",
            style=discord.ButtonStyle.green,
            custom_id="play_all"
        )
        play_all_btn.callback = self._play_all_callback

        stop_all_btn = ui.Button(
            emoji=ButtonIcons.STOP.value,
            label="Остановить все",
            style=discord.ButtonStyle.red,
            custom_id="stop_all"
        )
        stop_all_btn.callback = self._stop_all_callback

        skip_btn = ui.Button(
            emoji=ButtonIcons.SKIP.value,
            label="Пропустить",
            style=discord.ButtonStyle.secondary,
            custom_id="skip_song"
        )
        skip_btn.callback = self._skip_callback

        playlist_options = []
        playlist_path = config.PLAYLIST_PATH

        voice_state = self.ctx.voice_state
        current_playlist_path = None
        if voice_state and voice_state.playlist_manager:
            current_playlist_path = voice_state.playlist_manager.json_path

        if os.path.exists(playlist_path):
            for file in os.listdir(playlist_path):
                if file.endswith('.json'):
                    file_path = os.path.join(playlist_path, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            track_count = len(data) if isinstance(data, list) else 0
                    except:
                        track_count = 0

                    is_default = (current_playlist_path == file_path)

                    playlist_options.append(
                        SelectOption(
                            emoji="📁",
                            label=f"{file.replace('.json', '')} ╎ Треков: {track_count}",
                            value=file_path,
                            default=is_default
                        )
                    )

        if not playlist_options:
            playlist_options.append(
                SelectOption(
                    label="❌ Нет плейлистов",
                    value="",
                    default=True
                )
            )

        playlist_select = ui.Select(
            placeholder="Выберите плейлист...",
            options=playlist_options,
            custom_id="playlist_select"
        )
        playlist_select.callback = self._set_playlist_callback

        select_row = ui.ActionRow(playlist_select)
        action_row = ui.ActionRow(play_all_btn, stop_all_btn, skip_btn)

        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.container.add_item(select_row)
        self.container.add_item(action_row)

    def _add_volume_buttons(self):
        volume_down = ui.Button(
            emoji=ButtonIcons.VOLUME_DOWN.value,
            style=discord.ButtonStyle.gray,
            custom_id=ButtonAction.VOLUME_DOWN.value
        )
        volume_down.callback = self._create_volume_callback(-0.1)

        self.volume_display = ui.Button(
            label=f'{float_to_present(self._volume)}%',
            disabled=True,
            style=discord.ButtonStyle.gray,
            custom_id="volume_display"
        )

        volume_up = ui.Button(
            emoji=ButtonIcons.VOLUME_UP.value,
            style=discord.ButtonStyle.gray,
            custom_id=ButtonAction.VOLUME_UP.value
        )
        volume_up.callback = self._create_volume_callback(0.1)

        reset_btn = ui.Button(
            emoji=ButtonIcons.REPEAT.value,
            style=discord.ButtonStyle.gray,
            custom_id="reset_menu"
        )
        reset_btn.callback = self._reset_menu_callback

        action_row = ui.ActionRow(volume_down, self.volume_display, volume_up, reset_btn)

        self.container.add_item(action_row)

    def _add_preset_buttons(self):
        action_row = ui.ActionRow()
        for action, value in VOLUME_PRESETS.items():
            emojis = {
                ButtonAction.VOLUME_10: ButtonIcons.VOLUME_10,
                ButtonAction.VOLUME_50: ButtonIcons.VOLUME_50,
                ButtonAction.VOLUME_100: ButtonIcons.VOLUME
            }
            button = ui.Button(
                emoji=emojis[action].value if action is not ButtonAction.VOLUME_QUIET else ButtonIcons.VOLUME.value,
                style=discord.ButtonStyle.gray,
                custom_id=action.value,
            )
            button.callback = self._create_preset_callback(value)
            action_row.add_item(button)

        self.container.add_item(action_row)

    def _add_playback_buttons(self):
        stop_btn = ui.Button(
            emoji=ButtonIcons.STOP.value,
            style=discord.ButtonStyle.danger,
            custom_id=ButtonAction.STOP.value
        )
        stop_btn.callback = self._create_playback_callback(ButtonAction.STOP)

        voice = self.ctx.voice_state.voice
        is_actually_playing = voice and voice.is_playing()
        is_paused = self.player.is_paused

        if is_actually_playing and not is_paused:
            play_pause_btn = ui.Button(
                emoji=ButtonIcons.PAUSE.value,
                style=discord.ButtonStyle.primary,
                custom_id=ButtonAction.PAUSE.value
            )
            play_pause_btn.callback = self._create_playback_callback(ButtonAction.PAUSE)
        else:
            play_pause_btn = ui.Button(
                emoji=ButtonIcons.RESUME.value,
                style=discord.ButtonStyle.primary,
                custom_id=ButtonAction.RESUME.value
            )
            play_pause_btn.callback = self._create_playback_callback(ButtonAction.RESUME)

        voice_state = self.ctx.voice_state
        is_connected = voice_state.is_connected() if hasattr(voice_state, 'is_connected') else (
                    voice_state.voice is not None and voice_state.voice.is_connected())

        connection_btn = ui.Button(
            emoji=ButtonIcons.DISCONNECT.value if is_connected else ButtonIcons.CONNECT.value,
            label="Отключиться" if is_connected else "Подключиться",
            style=discord.ButtonStyle.red if is_connected else discord.ButtonStyle.green,
            custom_id="toggle_connection"
        )
        connection_btn.callback = self._toggle_connection_callback

        action_row = ui.ActionRow(stop_btn, play_pause_btn, connection_btn)
        self.container.add_item(action_row)

    def _create_volume_callback(self, delta: float):
        async def callback(inter: discord.Interaction):
            if not self.ctx.voice_state.voice:
                await inter.response.defer()
                return

            voice = self.ctx.voice_state.voice

            if voice.source is None:
                return

            try:
                new_volume = max(0, min(1, voice.source.volume + delta))
                voice.source.volume = new_volume
                self._volume = new_volume
                await self._update_volume_display(inter)
            except AttributeError:
                return

        return callback

    def _create_preset_callback(self, target_volume: float):
        async def callback(inter: discord.Interaction):
            if not self.ctx.voice_state.voice:
                await inter.response.defer()
                return

            voice = self.ctx.voice_state.voice

            if voice.source is None:
                return

            try:
                voice.source.volume = target_volume
                self._volume = target_volume
                await self._update_volume_display(inter)
            except AttributeError:
                return

        return callback

    def _create_playback_callback(self, action: ButtonAction):
        async def callback(inter: discord.Interaction):
            if not self.ctx.voice_state.voice:
                await inter.response.defer()
                return

            if action == ButtonAction.STOP:
                await self._handle_stop(inter)
            elif action == ButtonAction.PAUSE:
                await self._handle_pause(inter)
            elif action == ButtonAction.RESUME:
                await self._handle_resume(inter)

        return callback

    async def _handle_stop(self, inter: discord.Interaction):
        voice = self.ctx.voice_state.voice

        if voice and voice.is_playing():

            if voice.is_paused():
                await inter.followup.send(embed=BaseEmbeds.error("❌ Воспроизведение на паузу"))

            voice.stop()
            self.player.stop()

            self.ctx.voice_state._is_playing_playlist = False
            self.ctx.voice_state._is_playing_single = False
            self.ctx.voice_state.current = None

            if inter.response and not inter.response.is_done():
                await inter.response.defer()

            archive = self.ctx.menu_state.player.embeds[0]
            await self.ctx.menu_state.player.edit(embeds=[archive, BaseEmbeds.player()])

            new_view = ControlButtons(self.ctx, self.player)
            if inter.response:
                await inter.response.edit_message(view=new_view)

    async def _handle_pause(self, inter: discord.Interaction):
        voice = self.ctx.voice_state.voice
        if voice and voice.is_playing():
            voice.pause()
            self.player.pause()
            await self._rebuild_view(inter)

    async def _handle_resume(self, inter: discord.Interaction):
        voice = self.ctx.voice_state.voice
        if voice:
            voice.resume()
            self.player.resume()
            await self._rebuild_view(inter)

    @interaction_error_handler(logger)
    async def _toggle_connection_callback(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state

        if voice_state.is_connected():
            if voice_state.is_playing:
                voice_state.voice.stop()

            await voice_state.stop()
            await self._reset_menu_callback(inter)
        else:
            if not inter.user.voice:
                await inter.followup.send(embed=BaseEmbeds.error("❌ Вы не в голосовом канале!"), ephemeral=True)
                return

            destination = inter.user.voice.channel

            try:
                voice_state.voice = await destination.connect(timeout=20.0, reconnect=True)
            except Exception as e:
                logger.error(f"❌ Ошибка подключения: {e}")
                await inter.followup.send(BaseEmbeds.error(f"❌ Ошибка подключения: {str(e)[:100]}"), ephemeral=True)
                return

        new_view = MusicControlView(self.ctx, self.player, self._volume)
        await self.ctx.menu_state.menu.edit(view=new_view)

    async def _update_volume_display(self, inter: discord.Interaction):
        voice = self.ctx.voice_state.voice

        if voice and voice.source and hasattr(voice.source, 'volume'):
            new_volume = voice.source.volume
            self._volume = new_volume
            self.volume_display.label = f'{float_to_present(new_volume)}%'
        else:
            self.volume_display.label = f'{float_to_present(self._volume)}%'

        new_view = MusicControlView(self.ctx, self.player, self._volume)
        await inter.response.edit_message(view=new_view)

    async def _rebuild_view(self, inter: discord.Interaction):
        new_volume = self.ctx.voice_state.voice.source.volume if self.ctx.voice_state.voice else self._volume
        new_view = MusicControlView(self.ctx, self.player, new_volume)
        await inter.response.edit_message(view=new_view)

    @interaction_error_handler(logger)
    async def _play_all_callback(self, inter: discord.Interaction):
        await _ensure_voice_connection(self.ctx, inter)

        await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state

        if not self.ctx.voice_state.is_connected():
            await inter.followup.send(embed=BaseEmbeds.error("❌ Бот не в голосовом канале!"), ephemeral=True)
            return

        if not voice_state.playlist_manager or voice_state.playlist_manager.is_empty:
            await inter.followup.send(embed=BaseEmbeds.error("❌ Плейлист не загружен или пуст!"), ephemeral=True)
            return

        await voice_state.start_playlist(self.ctx.menu_state.archive)

    @interaction_error_handler(logger)
    async def _stop_all_callback(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state
        voice_state._is_playing_playlist = False
        voice_state._is_playing_single = False

        if voice_state.is_connected() and voice_state.is_playing:
            voice_state.voice.stop()

        self.player.stop()
        await voice_state._stop_playback("⏹️ Воспроизведение остановлено")

    @interaction_error_handler(logger)
    async def _skip_callback(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state

        if not voice_state.is_connected() or not voice_state.is_playing:
            return

        if voice_state._is_playing_single:
            voice_state.voice.stop()
            return

        if voice_state._is_playing_playlist and voice_state.playlist_manager:
            current_track = voice_state.playlist_manager.get_current_track()
            is_last = voice_state.playlist_manager.get_next_track() is None

            voice_state.skip()

            if is_last:
                voice_state._is_playing_playlist = False
                await voice_state._stop_playback("✅ Все треки воспроизведены!")
        else:
            voice_state.skip()

    @interaction_error_handler(logger)
    async def _set_playlist_callback(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state

        if not self.ctx.voice_state.is_connected():
            await inter.followup.send(embed=BaseEmbeds.error("❌ Бот не в голосовом канале!"), ephemeral=True)
            return

        selected_value = inter.data["values"][0]
        if not selected_value:
            await inter.followup.send(embed=BaseEmbeds.error("❌ Плейлист не выбран!"), ephemeral=True)
            return

        voice_state.load_playlist(selected_value)

        if voice_state.playlist_manager and not voice_state.playlist_manager.is_empty:
            await inter.followup.send(
                embed=BaseEmbeds.info(f"✅ Загружен плейлист **{Path(selected_value).stem}** ({voice_state.playlist_manager.total} треков)"),
                ephemeral=True
            )
        else:
            await inter.followup.send(embed=BaseEmbeds.error(f"❌ Ошибка загрузки плейлиста!"), ephemeral=True)

    @interaction_error_handler(logger)
    async def _reset_menu_callback(self, inter: discord.Interaction):
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        voice_state = self.ctx.voice_state

        if voice_state.is_playing:
            voice_state.voice.stop()

        voice_state._is_playing_playlist = False
        voice_state._is_playing_single = False
        voice_state.current = None

        if self.ctx.menu_state and self.ctx.menu_state.music_player:
            self.ctx.menu_state.music_player.stop()

        if self.ctx.menu_state and self.ctx.menu_state.player:
            self.ctx.menu_state.archive = Archive()
            archive_embed = self.ctx.menu_state.player.embeds[0].clear_fields()
            await self.ctx.menu_state.player.edit(embeds=[BaseEmbeds.archive(), BaseEmbeds.player()], view=ControlButtons(self.ctx, self.ctx.menu_state.music_player))

        await self.ctx.menu_state.menu.edit(
            view=MusicControlView(self.ctx, self.ctx.menu_state.music_player, self._volume)
        )


async def _ensure_voice_connection(ctx: commands.Context, inter: discord.Interaction):
    if not ctx.voice_state.is_connected():
        if not inter.user.voice:
            await inter.response.send_message(embed=BaseEmbeds.error("❌ Вы не в голосовом канале!"), ephemeral=True)
            return

        destination = inter.user.voice.channel

        if ctx.voice_state.is_playing:
            await ctx.voice_state.stop()

        ctx.voice_state.voice = await destination.connect()


def float_to_present(volume: float) -> int:
    return round(volume * 100)
