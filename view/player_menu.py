
import asyncio
import datetime
from typing import Optional

import discord

from discord.ext import commands

import config

from utils.song_embed import AudioFile


class PlayerContext:
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx

        self.player = None
        self.menu = None

    def __del__(self):
        self.player = None
        self.menu = None


class MusicPlayer:
    """Класс для управления состоянием воспроизведения."""

    def __init__(self, ctx: commands.Context, companents: list):

        self.counter_task = None  
        self.is_paused = False 
        self.is_queue = False  
        self.start_time = None 
        self.elapsed_time = 0

        self.ctx: commands.Context = ctx
        self.components = companents

    async def start_counter(self, song: AudioFile, player_message):
        """Запускает счётчик."""
        archive = self.ctx.menu_state.player.embeds[0]
        player = self.ctx.menu_state.player.embeds[1]

        player.description = f'```{song.filename.split("/")[-1].split(".")[0]}```'

        while self.elapsed_time < song.duration:
            if not self.is_paused:
                current_time = discord.utils.utcnow()
                self.elapsed_time = (current_time - self.start_time).total_seconds()
                player.set_footer(text=f'{self.seconds_to_hms(self.elapsed_time)} / {self.seconds_to_hms(song.duration)}')
                
                await player_message.edit(embeds=[archive, player])
                
            await asyncio.sleep(1)
        else:
            await player_message.edit(embeds=[archive, discord.Embed(title='Сейчас играет 🎶:',color=config.COLOR, description='```Сейчас ничего не играет :(```')])
            self.stop()

    def seconds_to_hms(self, seconds):
        """Преобразует секунды в формат ЧЧ:ММ:СС."""

        seconds = round(seconds)

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes:02}:{seconds:02}"

    def start(self, duration, message):
        """Запускает воспроизведение."""
        if not self.counter_task:
            self.start_time = discord.utils.utcnow()
            self.counter_task = asyncio.create_task(self.start_counter(duration, message))

    def pause(self):
        """Приостанавливает воспроизведение."""
        if not self.is_paused:
            self.is_paused = True
            self.elapsed_time = (discord.utils.utcnow() - self.start_time).total_seconds()

    def resume(self):
        """Возобновляет воспроизведение."""
        if self.is_paused:
            self.is_paused = False
            self.start_time = discord.utils.utcnow() - datetime.timedelta(seconds=self.elapsed_time)

    def queue(self):
        self.is_queue = not(self.is_queue)

    def stop(self):
        """Останавливает воспроизведение."""
        if self.counter_task:
            self.counter_task.cancel()
            self.counter_task = None
            self.is_paused = False
            self.elapsed_time = 0
            self.start_time = None


def float_to_present(volume: float):
        return round(round(volume, 2) * 100)
    

class Buttons(discord.ui.View):
    def __init__(self, ctx: commands.Context, player: MusicPlayer):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx

        self.player = player

        for data in player.components:
            button = discord.ui.Button(label=data['label'], style=data['style'], custom_id=data['custom_id'])

            if self.player.is_queue:
                button.style = discord.ButtonStyle.blurple
                button.callback = self.queue_button_callback
            else:
                button.callback = self.button_callback

            self.add_item(button)

    # noinspection PyTypeChecker
    async def button_callback(self, inter: discord.Interaction):
        button_id = inter.data.get('custom_id')

        if not self.ctx.voice_state.voice:
            destination = self.ctx.author.voice.channel
            if self.ctx.voice_state.voice:
                await self.ctx.voice_state.voice.move_to(destination)
                return

            if self.ctx.voice_state.is_playing:
                await self.ctx.voice_state.stop()

            self.ctx.voice_state.voice = await destination.connect()

        file = AudioFile(button_id, self.ctx.menu_state.player)

        await self.ctx.voice_state.play_file(file)

        await self.ctx.menu_state.menu.edit(view=MenuButtons(self.ctx, self.player, file.volume))
        

        
    async def queue_button_callback(self, inter: discord.Interaction):
        button_id = inter.data.get('custom_id')
        
        if button_id.endswith('.webm') or button_id.endswith('.mp3') or button_id.endswith('.wav'):
            if not self.ctx.voice_state.voice:
                destination = self.ctx.author.voice.channel
                if self.ctx.voice_state.voice:
                    await self.ctx.voice_state.voice.move_to(destination)
                    return
                
                if self.ctx.voice_state.is_playing:
                    await self.ctx.voice_state.stop()
                
                self.ctx.voice_state.voice = await destination.connect()

            file = AudioFile(button_id, self.ctx.menu_state.player)
            
            await self.ctx.voice_state.songs.put(file)
            
            await self.ctx.menu_state.menu.edit(view=MenuButtons(self.ctx, self.player, file.volume))
        
        await inter.response.defer()


# noinspection PyUnresolvedReferences
class MenuButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, player: MusicPlayer, volume: float = None):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None
        self.ctx = ctx
        self._volume = volume

        self.player = player

        self.minus_volume_button = discord.ui.Button(emoji="🔉", style=discord.ButtonStyle.gray, custom_id='volume-', row=1)
        self.minus_volume_button.callback = self.minus_volume_callback

        self.volume_button = discord.ui.Button(label=f'{self._volume * 100}%', disabled=True, style=discord.ButtonStyle.gray, custom_id='volume', row=1)
        
        self.plus_volume_button = discord.ui.Button(emoji='🔊', style=discord.ButtonStyle.gray, custom_id='volume+', row=1)
        self.plus_volume_button.callback = self.plus_volume_callback

        self.quiet_button = discord.ui.Button(emoji='🔈', style=discord.ButtonStyle.gray, custom_id='quiet', row=2)
        self.quiet_button.callback = self.quiet_volume_callback

        self.volume_button_10 = discord.ui.Button(label='10', style=discord.ButtonStyle.gray, custom_id='volume_10', row=2)
        self.volume_button_10.callback = self.volume_10_callback

        self.volume_button_50 = discord.ui.Button(label='50', style=discord.ButtonStyle.gray, custom_id='volume_50', row=2)
        self.volume_button_50.callback = self.volume_50_callback

        self.stop_button = discord.ui.Button(emoji='⏹', style=discord.ButtonStyle.gray, custom_id='stop_button', row=3)
        self.stop_button.callback = self.stop_button_callback

        self.pause_button = discord.ui.Button(emoji='⏸', style=discord.ButtonStyle.gray, custom_id='pause_button', row=3)
        self.pause_button.callback = self.pause_button_callback

        self.resume_button = discord.ui.Button(emoji='▶', style=discord.ButtonStyle.gray, custom_id='resume_button', row=3)
        self.resume_button.callback = self.resume_button_callback

        self.queue_button = discord.ui.Button(emoji='🔁', style=discord.ButtonStyle.blurple, custom_id='queue_button', row=3)
        self.queue_button.callback = self.queue_button_callback

        self.add_item(self.minus_volume_button)
        self.add_item(self.volume_button)
        self.add_item(self.plus_volume_button)
        self.add_item(self.quiet_button)
        self.add_item(self.volume_button_10)
        self.add_item(self.volume_button_50)
        self.add_item(self.stop_button)

        if self.ctx.voice_state.voice.is_paused():
            self.add_item(self.resume_button)
        else:
            self.add_item(self.pause_button)
        
        self.add_item(self.queue_button)

    async def minus_volume_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            if self.ctx.voice_state.voice.source.volume >= 0:
                self.ctx.voice_state.voice.source.volume -= 10 / 100
                await self.update_volume(inter)
        else:
            await inter.response.defer()

    async def plus_volume_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            if self.ctx.voice_state.voice.source.volume <= 100 / 100:
                self.ctx.voice_state.voice.source.volume += 10 / 100
                await self.update_volume(inter)
        else:
            await inter.response.defer()
    
    async def quiet_volume_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            self.ctx.voice_state.voice.source.volume = 0
            await self.update_volume(inter)
        else:
            await inter.response.defer()
    
    async def volume_10_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            self.ctx.voice_state.voice.source.volume = 10 / 100
            await self.update_volume(inter)
        else:
            await inter.response.defer()
    
    async def volume_50_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            self.ctx.voice_state.voice.source.volume = 50 / 100
            await self.update_volume(inter)
        else:
            await inter.response.defer()
    
    async def stop_button_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.voice:
            if self.ctx.voice_state.is_playing:
                self.ctx.voice_state.voice.stop()
                self.player.stop()

                archive = self.ctx.menu_state.player.embeds[0]
                await self.ctx.menu_state.player.edit(embeds=[archive, discord.Embed(description='```Сейчас ничего не играет :(```')])
        await inter.response.defer()
    
    async def pause_button_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.is_playing and self.ctx.voice_state.voice.is_playing():
            self.ctx.voice_state.voice.pause()
            self.player.pause()

            await self.update_volume(inter)
        await inter.response.defer()
    
    async def resume_button_callback(self, inter: discord.Interaction):
        if self.ctx.voice_state.is_playing and self.ctx.voice_state.voice.is_paused():
            self.ctx.voice_state.voice.resume()
            self.player.resume()

            await self.update_volume(inter)
        await inter.response.defer()
    
    async def queue_button_callback(self, inter: discord.Interaction):
        
        self.player.queue()
        await self.update_buttons()
        
        await inter.response.defer()
    
    async def update_volume(self, inter: discord.Interaction):
        volume = self.ctx.voice_state.voice.source.volume
        button = MenuButtons(ctx=self.ctx, volume=volume, player=self.player)
        
        button.minus_volume_button.disabled = volume <= 0.1
        button.plus_volume_button.disabled = volume > 0.9
        button.quiet_button.disabled = volume == 0
        button.volume_button_10.disabled = volume == 10 / 100
        button.volume_button_50.disabled = volume == 50 / 100

        button.volume_button.label = f'{float_to_present(volume)}%'

        await inter.response.edit_message(view=button)
    
    async def update_buttons(self):
        await self.ctx.menu_state.player.edit(view=Buttons(self.ctx, self.player))