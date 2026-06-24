import math
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import config

from data.data_classes.archive import Archive
from utils.logger import BotLogger
from utils.sort_utils import first_number
from utils.voice_utils import VoiceState, VoiceError
from view.player_menu_view import MusicPlayer, ControlButtons, MusicControlView, float_to_present, PlayerContext


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)
        self.voice_states = {}
        self.menu_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)

            self.voice_states[ctx.guild.id] = state

        return state

    def get_menu_state(self, ctx: commands.Context) -> PlayerContext:
        channel_id = ctx.channel.id
        if channel_id not in self.menu_states:
            self.menu_states[channel_id] = PlayerContext(ctx)
        return self.menu_states[channel_id]

    def cleanup_menu_state(self, ctx: commands.Context):
        channel_id = ctx.channel.id
        if channel_id in self.menu_states:
            state = self.menu_states[channel_id]

            if state.archive:
                asyncio.create_task(state.archive.delete())
            if state.player:
                asyncio.create_task(state.player.delete())
            if state.menu:
                asyncio.create_task(state.menu.delete())

            state.cleanup()
            del self.menu_states[channel_id]

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)
        ctx.menu_state = self.get_menu_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.hybrid_command(name='join')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _join(self, ctx: commands.Context):
        destination = ctx.author.voice.channel

        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="Вы не в голосовом канале!", color=config.COLOR), ephemeral=True)
            return

        if ctx.voice_state.voice and ctx.voice_state.voice.is_connected():
            await ctx.voice_state.voice.move_to(destination)
            return

        try:
            ctx.voice_state.voice = await destination.connect(timeout=20.0, reconnect=True)
        except Exception as e:
            self.logger.error(f"Ошибка подключения: {e}")

    @commands.hybrid_command(name='summon')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.hybrid_command(name='leave', aliases=['disconnect'])
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _leave(self, ctx: commands.Context):
        if not ctx.voice_state.voice:
            return await ctx.send(
                embed=discord.Embed(description='Бот не подключен ни к одному голосовому каналу', color=config.COLOR), ephemeral=True)

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.hybrid_command(name='volume')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _volume(self, ctx: commands.Context, *, volume: int):
        if not ctx.voice_state.is_playing:
            return await ctx.send(embed=discord.Embed(description='Сейчас ничего не играет', color=config.COLOR), ephemeral=True)

        if 0 > volume < 100:
            return await ctx.send(
                embed=discord.Embed(description='Громкость должна быть от 0 до 100', color=config.COLOR), ephemeral=True)

        ctx.voice_state.voice.source.volume = volume / 100
        await ctx.send(
            embed=discord.Embed(description='Громкость: {}%'.format(volume), color=config.COLOR), ephemeral=True)

    @commands.hybrid_command(name='pause')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _pause(self, ctx: commands.Context):
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()

        await ctx.interaction.response.defer()

    @commands.hybrid_command(name='resume')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _resume(self, ctx: commands.Context):
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()

        await ctx.interaction.response.defer()

    @commands.hybrid_command(name='stop')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _stop(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()

        await ctx.interaction.response.defer()

    @commands.hybrid_command(name='play_file')
    @app_commands.describe(
        filename='Принимает пути к файлам в формате "path/to/file.mp3", файл предварительно должен быть скачен папку'
    )
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def play_file(self, ctx: commands.Context, *, filename: str):
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            await ctx.voice_state.play_file(discord.FFmpegPCMAudio(f'audio_files/{filename}'))

            await ctx.send(
                embed=discord.Embed(description=f'🎶 **Добавлено из файла**: ```{filename}```', color=config.COLOR))

    @_join.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client and ctx.voice_client.is_connected():
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.move_to(ctx.author.voice.channel)

    @commands.hybrid_command(name='menu')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def menu(self, ctx: commands.Context, folder: str):
        self.cleanup_menu_state(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)

        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="Вы не в голосовом канале!", color=config.COLOR), ephemeral=True)
            return

        channel = ctx.channel
        folder_path = f'./audio_files/{folder}'

        if not os.path.exists(folder_path):
            await ctx.send(embed=discord.Embed(description=f"Папка `{folder}` не найдена!", color=config.COLOR), ephemeral=True)
            return

        content = os.listdir(folder_path)
        components = []

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        for file in content:
            if not any(file.endswith(ext) for ext in ('.mp3', '.webm', '.wav')):
                continue

            if len(file) >= 70:

                os.rename(f'{folder_path}/{file}', f'{folder_path}/{file[:60]}.{file.split('.')[-1]}')
                label = f'{file.split(".")[0][:60]}...'
                custom_id = f'{folder_path}/{file[:60]}.{file.split('.')[-1]}'
            else:
                label = file.split('.')[0]
                custom_id = f'{folder_path}/{file}'

            components.append({'label': label, 'style': discord.ButtonStyle.green, 'custom_id': custom_id})

            if len(components) == 25:
                await channel.send(view=ControlButtons(ctx, MusicPlayer(ctx, components)))
                components.clear()

        if components:
            components = sorted(components, key=lambda x: first_number(x['label']))

        archive_embed = discord.Embed(title='Архив', color=config.COLOR)
        player_embed = discord.Embed(title='Сейчас играет 🎶:', color=config.COLOR, description='```Сейчас ничего не играет :(```')

        music_player = MusicPlayer(ctx, components)
        archive = Archive()
        ctx.menu_state.music_player = music_player
        ctx.menu_state.archive = archive

        ctx.menu_state.player = await channel.send(embeds=[archive_embed, player_embed], view=ControlButtons(ctx, music_player))
        ctx.menu_state.menu = await channel.send(view=MusicControlView(ctx, music_player, 50 / 100))

        await ctx.interaction.delete_original_response()

    @commands.hybrid_command(name="load_playlist")
    @commands.has_permissions(administrator=True)
    async def load_playlist(self, ctx: commands.Context, json_path: str):
        """Загрузить плейлист из JSON: !load_playlist playlist.json"""

        voice_state = ctx.voice_state

        if not voice_state.voice:
            await ctx.send("❌ Бот не в голосовом канале!")
            return

        if not Path(json_path).exists():
            await ctx.send(f"❌ Файл `{json_path}` не найден!")
            return

        voice_state.load_playlist(json_path)

        if not voice_state.playlist_manager.is_empty:
            await ctx.send(f"✅ Загружено {voice_state.playlist_manager.total} треков из `{json_path}`!")
            await ctx.send("▶️ Нажмите кнопку **Воспроизвести все** для начала!")
        else:
            await ctx.send(f"❌ Ошибка загрузки плейлиста из `{json_path}`!")

    @commands.hybrid_command(name="playlist_info")
    async def playlist_info(self, ctx: commands.Context):
        """Показать информацию о плейлисте"""
        voice_state = ctx.voice_state

        if not voice_state.playlist_manager or voice_state.playlist_manager.is_empty:
            await ctx.send("📭 Плейлист не загружен!")
            return

        pm = voice_state.playlist_manager

        embed = discord.Embed(
            title="🎵 Информация о плейлисте",
            description=f"Всего треков: {pm.total}\n"
                        f"Осталось: {pm.remaining}\n"
                        f"Текущий индекс: {pm.current_index + 1}",
            color=discord.Color.blue()
        )

        # Показываем текущий и следующий треки
        current = pm.get_current_track()
        if current:
            name = Path(current.get("track", "")).stem
            embed.add_field(
                name="▶️ Текущий трек",
                value=f"`{name}`\n"
                      f"Старт: {current.get('start_delay', 0)}с | Энд: {current.get('end_delay', 0)}с",
                inline=False
            )

        next_track = pm.get_next_track()
        if next_track:
            name = Path(next_track.get("track", "")).stem
            embed.add_field(
                name="⏭️ Следующий трек",
                value=f"`{name}`\n"
                      f"Старт: {next_track.get('start_delay', 0)}с | Энд: {next_track.get('end_delay', 0)}с",
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
