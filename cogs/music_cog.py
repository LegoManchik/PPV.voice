import math
import os
import json
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
                embed=discord.Embed(description='Бот не подключен ни к одному голосовому каналу', color=config.COLOR),
                ephemeral=True)

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.hybrid_command(name='volume')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _volume(self, ctx: commands.Context, *, volume: int):
        if not ctx.voice_state.is_playing:
            return await ctx.send(embed=discord.Embed(description='Сейчас ничего не играет', color=config.COLOR),
                                  ephemeral=True)

        if 0 > volume < 100:
            return await ctx.send(
                embed=discord.Embed(description='Громкость должна быть от 0 до 100', color=config.COLOR),
                ephemeral=True)

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
    @app_commands.describe(
        folder="Папка с аудиофайлами"
    )
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def menu(self, ctx: commands.Context, folder: str):
        self.cleanup_menu_state(ctx)

        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="❌ Вы не в голосовом канале!"), ephemeral=True)
            return

        folder_path = f'./audio_files/{folder}'
        if not os.path.exists(folder_path):
            await ctx.send(embed=discord.Embed(description=f"❌ Папка `{folder}` не найдена!"), ephemeral=True)
            return

        if not ctx.voice_state.voice or not ctx.voice_state.voice.is_connected():
            try:
                destination = ctx.author.voice.channel
                ctx.voice_state.voice = await destination.connect(timeout=20.0, reconnect=True)
            except Exception as e:
                await ctx.send(embed=discord.Embed(description=f"❌ Ошибка подключения: {str(e)[:100]}"), ephemeral=True)
                return

        await ctx.send(embed=discord.Embed(description="🔄 Загрузка меню..."), ephemeral=True)

        content = os.listdir(folder_path)

        components = []
        for file in content:
            if not any(file.endswith(ext) for ext in ('.mp3', '.webm', '.wav')):
                continue
            label = file.split('.')[0]
            custom_id = f'{folder_path}/{file}'
            components.append({'label': label, 'style': discord.ButtonStyle.green, 'custom_id': custom_id})

        music_player = MusicPlayer(ctx, sorted(components, key=lambda x: first_number(x['label'])))
        archive = Archive()

        ctx.menu_state.music_player = music_player
        ctx.menu_state.archive = archive

        archive_embed = discord.Embed(title='Архив', color=config.COLOR)
        player_embed = discord.Embed(
            title='Сейчас играет 🎶:',
            color=config.COLOR,
            description='```Сейчас ничего не играет :(```'
        )

        ctx.menu_state.player = await ctx.channel.send(
            embeds=[archive_embed, player_embed],
            view=ControlButtons(ctx, music_player)
        )

        ctx.menu_state.menu = await ctx.channel.send(
            view=MusicControlView(ctx, music_player, 0.5)
        )

        await ctx.interaction.delete_original_response()

    @commands.hybrid_command(name='add_playlist')
    @app_commands.describe(
        playlist=".json файл с массивом треков"
    )
    @commands.has_permissions(administrator=True)
    async def add_playlist(self, ctx: commands.Context, playlist: discord.Attachment):
        if not playlist.filename.endswith('.json'):
            await ctx.send(embed=discord.Embed(description="❌ Файл должен быть в формате `.json`!", color=discord.Color.red()), ephemeral=True)
            return

        if playlist.size > 1024 * 1024:
            await ctx.send(embed=discord.Embed(description="❌ Файл слишком большой! Максимум 1MB.", color=discord.Color.red()), ephemeral=True)
            return

        try:
            content = await playlist.read()
            data = json.loads(content.decode('utf-8'))

            if not isinstance(data, list):
                await ctx.send(embed=discord.Embed(description="❌ Неверная структура JSON! Ожидается массив треков.", color=discord.Color.red()), ephemeral=True)
                return

            for i, track in enumerate(data):
                if not isinstance(track, dict):
                    await ctx.send(embed=discord.Embed(description=f"❌ Ошибка в треке {i + 1}: ожидается объект.", color=discord.Color.red()), ephemeral=True)
                    return
                if 'track' not in track:
                    await ctx.send(embed=discord.Embed(description=f"❌ Ошибка в треке {i + 1}: отсутствует поле 'track'.", color=discord.Color.red()), ephemeral=True)
                    return
                if not Path(track['track']).exists():
                    await ctx.send(embed=discord.Embed(description=f"⚠️ Предупреждение: файл `{track['track']}` не найден, но плейлист будет добавлен.", color=discord.Color.red()),
                                   ephemeral=True)

            playlist_path = config.PLAYLIST_PATH
            os.makedirs(playlist_path, exist_ok=True)

            base_name = playlist.filename.replace('.json', '')
            save_path = os.path.join(playlist_path, f"{base_name}.json")

            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(playlist_path, f"{base_name}_{counter}.json")
                counter += 1

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            await ctx.send(embed=discord.Embed(
                title=f"✅ Плейлист `{os.path.basename(save_path)}` добавлен!\n",
                description=f"📁 Сохранён в: `{save_path}`\n"
                            f"🎵 Треков: {len(data)}",
                color=config.COLOR),
                ephemeral=True
            )

        except json.JSONDecodeError as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Ошибка парсинга JSON: {e}", color=discord.Color.red()), ephemeral=True)
        except Exception as e:
            self.logger.error(f"Ошибка добавления плейлиста: {e}")
            await ctx.send(embed=discord.Embed(description=f"❌ Ошибка: {str(e)[:100]}", color=discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
