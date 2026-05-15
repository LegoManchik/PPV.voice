import asyncio
import datetime
import traceback
from enum import Enum
from typing import Optional, List, Dict, Any

import discord
from discord import ui
from discord.ext import commands

import config
from utils.logger import interaction_error_handler
from utils.song_embed import AudioFile


class PlayerState(Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


class ButtonEmojis(Enum):
    PAUSE = "<:pause:1501539835922616461>"
    RESUME = "<:resume:1501539806004645928>"
    STOP = "<:stop:1501546908257095791>"
    REPEAT = "<:repeat:1501560148588757044>"
    VOLUME = "<:volume:1501555461919604927>"
    VOLUME_UP = "<:volume_up:1501545557058125954>"
    VOLUME_DOWN = "<:volume_down:1501545554512056423>"
    VOLUME_10 = "<:volume_10:1501553579972886679>"
    VOLUME_50 = "<:volume_50:1501553577544515635>"


class ButtonAction(Enum):
    VOLUME_DOWN = "volume-"
    VOLUME_UP = "volume+"
    VOLUME_QUIET = "quiet"
    VOLUME_10 = "volume_10"
    VOLUME_50 = "volume_50"
    STOP = "stop_button"
    PAUSE = "pause_button"
    RESUME = "resume_button"


VOLUME_PRESETS = {
    ButtonAction.VOLUME_QUIET: 0,
    ButtonAction.VOLUME_10: 0.1,
    ButtonAction.VOLUME_50: 0.5,
}


class PlayerContext:
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.player: Optional['MusicPlayer'] = None
        self.menu: Optional[discord.Message] = None

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        self.player = None
        self.menu = None


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
        return self._state == PlayerState.PLAYING

    @property
    def is_paused(self) -> bool:
        return self._state == PlayerState.PAUSED

    async def start_counter(self, song: AudioFile, player_message: discord.Message):
        archive = self.ctx.menu_state.player.embeds[0]
        player_embed = self.ctx.menu_state.player.embeds[1]
        song_name = song.filename.split("/")[-1].split(".")[0]

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

                current_time_str = self._format_time(self, self._elapsed_time)
                total_time_str = self._format_time(self, song.duration)

                footer_text = f'{current_time_str} / {total_time_str} {bar}'
                player_embed.set_footer(text=footer_text)

                await player_message.edit(embeds=[archive, player_embed])

            await asyncio.sleep(0.5)

        if self._state != PlayerState.STOPPED:
            await self._stop_playback(player_message)

    async def _stop_playback(self, player_message: discord.Message):
        archive = self.ctx.menu_state.player.embeds[0]
        empty_embed = discord.Embed(
            title='Сейчас играет 🎶:',
            color=config.COLOR,
            description='```Сейчас ничего не играет :(```'
        )
        await player_message.edit(embeds=[archive, empty_embed])
        self.stop()

    @staticmethod
    def _format_time(self, seconds: float) -> str:
        seconds = round(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        return f"{minutes:02}:{seconds:02}"

    def start(self, song: AudioFile, message: discord.Message):
        if not self._counter_task:
            self._current_song = song
            self._state = PlayerState.PLAYING
            self._start_time = discord.utils.utcnow()
            self._elapsed_time = 0

            self._counter_task = asyncio.create_task(self.start_counter(song, message))

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

    async def _add_to_archive(self, inter: discord.Interaction):
        archive: discord.Embed = self.ctx.menu_state.player.embeds[0]

        if len(archive.fields) == 25:
            archive.clear_fields()

        if len(archive.fields) > 0:
            old_prev = archive.fields[-1]
            archive.remove_field(-1)
            archive.add_field(name="", value=old_prev.value.split('/')[-1], inline=False)

        archive.add_field(name="Последний трек:", value=f"`{inter.custom_id.split('/')[-1]}`", inline=False)

        current_track = self.ctx.menu_state.player.embeds[1]
        await self.ctx.menu_state.player.edit(embeds=[archive, current_track])

    async def _handle_file_playback(self, inter: discord.Interaction, file_path: str):
        await self._ensure_voice_connection(inter)

        self.player.stop()

        if self._is_audio_file(self, file_path):
            await self._add_to_archive(inter)
            file = AudioFile(file_path, self.ctx.menu_state.player)
            await self.ctx.voice_state.play_file(file)

            await self._update_to_control_view(inter, file.volume)

    async def _ensure_voice_connection(self, inter: discord.Interaction):
        if not self.ctx.voice_state.voice:
            if not inter.user.voice:
                await inter.response.send_message("Вы не в голосовом канале!", ephemeral=True)
                return

            destination = inter.user.voice.channel

            if self.ctx.voice_state.is_playing:
                await self.ctx.voice_state.stop()

            self.ctx.voice_state.voice = await destination.connect()

    @staticmethod
    def _is_audio_file(self, file_path: str) -> bool:
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
        self._volume = volume or 0.5

        self.container = ui.Container(accent_color=config.COLOR)

        self._setup_buttons()
        ctx.bot.add_view(self)

    def _setup_buttons(self):
        self._add_volume_buttons()
        self._add_preset_buttons()
        self._add_playback_buttons()
        self.add_item(self.container)

    def _add_volume_buttons(self):
        volume_down = ui.Button(emoji=ButtonEmojis.VOLUME_DOWN.value, style=discord.ButtonStyle.gray, custom_id=ButtonAction.VOLUME_DOWN.value)
        volume_down.callback = self._create_volume_callback(-0.1)

        self.volume_display = ui.Button(
            label=f'{float_to_present(self._volume)}%',
            disabled=True,
            style=discord.ButtonStyle.gray,
            custom_id="volume_display"
        )

        volume_up = ui.Button(emoji=ButtonEmojis.VOLUME_UP.value, style=discord.ButtonStyle.gray, custom_id=ButtonAction.VOLUME_UP.value)
        volume_up.callback = self._create_volume_callback(0.1)

        action_row = ui.ActionRow(
            volume_down, self.volume_display, volume_up
        )
        self.container.add_item(action_row)

    def _add_preset_buttons(self):
        action_row = ui.ActionRow()
        for action, value in VOLUME_PRESETS.items():
            emojis = {
                ButtonAction.VOLUME_10: ButtonEmojis.VOLUME_10,
                ButtonAction.VOLUME_50: ButtonEmojis.VOLUME_50
            }
            button = ui.Button(
                emoji=emojis[action].value if action is not ButtonAction.VOLUME_QUIET else ButtonEmojis.VOLUME.value,
                style=discord.ButtonStyle.gray,
                custom_id=action.value,
            )
            button.callback = self._create_preset_callback(value)
            action_row.add_item(button)

        self.container.add_item(action_row)

    def _add_playback_buttons(self):
        stop_btn = ui.Button(emoji=ButtonEmojis.STOP.value, style=discord.ButtonStyle.danger, custom_id=ButtonAction.STOP.value)
        stop_btn.callback = self._create_playback_callback(ButtonAction.STOP)

        if self.ctx.voice_state.voice and self.ctx.voice_state.voice.is_playing():
            play_pause_btn = ui.Button(
                emoji=ButtonEmojis.PAUSE.value if not self.player.is_paused else ButtonEmojis.RESUME.value,
                style=discord.ButtonStyle.primary,
                custom_id=ButtonAction.PAUSE.value if not self.player.is_paused else ButtonAction.RESUME.value
            )
            play_pause_btn.callback = self._create_playback_callback(
                ButtonAction.PAUSE if not self.player.is_paused else ButtonAction.RESUME
            )
        else:
            play_pause_btn = ui.Button(emoji=ButtonEmojis.RESUME.value, style=discord.ButtonStyle.primary, custom_id=ButtonAction.RESUME.value)
            play_pause_btn.callback = self._create_playback_callback(ButtonAction.RESUME)

        action_row = ui.ActionRow(
            stop_btn, play_pause_btn
        )
        self.container.add_item(action_row)

    def _create_volume_callback(self, delta: float):
        async def callback(inter: discord.Interaction):
            if not self.ctx.voice_state.voice:
                await inter.response.defer()
                return

            new_volume = max(0, min(1, self.ctx.voice_state.voice.source.volume + delta))
            self.ctx.voice_state.voice.source.volume = new_volume
            await self._update_volume_display(inter)

        return callback

    def _create_preset_callback(self, target_volume: float):
        async def callback(inter: discord.Interaction):
            if not self.ctx.voice_state.voice:
                await inter.response.defer()
                return

            self.ctx.voice_state.voice.source.volume = target_volume
            await self._update_volume_display(inter)

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

            await inter.response.defer()

        return callback

    async def _handle_stop(self, inter: discord.Interaction):
        if self.ctx.voice_state.is_playing:
            self.ctx.voice_state.voice.stop()
            self.player.stop()

            if inter.response and not inter.response.is_done():
                await inter.response.defer()

            archive = self.ctx.menu_state.player.embeds[0]
            empty_embed = discord.Embed(description='```Сейчас ничего не играет :(```', color=config.COLOR)
            await self.ctx.menu_state.player.edit(embeds=[archive, empty_embed])

    async def _handle_pause(self, inter: discord.Interaction):
        if self.ctx.voice_state.is_playing and self.ctx.voice_state.voice.is_playing():
            self.ctx.voice_state.voice.pause()
            self.player.pause()
            await self._rebuild_view(inter)

    async def _handle_resume(self, inter: discord.Interaction):
        if self.ctx.voice_state.is_playing:
            self.ctx.voice_state.voice.resume()
            self.player.resume()
            await self._rebuild_view(inter)

    async def _update_volume_display(self, inter: discord.Interaction):
        new_volume = self.ctx.voice_state.voice.source.volume
        self.volume_display.label = f'{float_to_present(new_volume)}%'
        await inter.response.edit_message(view=self)

    async def _rebuild_view(self, inter: discord.Interaction):
        new_volume = self.ctx.voice_state.voice.source.volume if self.ctx.voice_state.voice else self._volume
        new_view = MusicControlView(self.ctx, self.player, new_volume)
        await inter.response.edit_message(view=new_view)


def float_to_present(volume: float) -> int:
    return round(volume * 100)
