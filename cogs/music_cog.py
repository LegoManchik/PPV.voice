import math
import os

from discord import app_commands

import config  # type: ignore
from utils.logger import BotLogger

from utils.sort_utils import first_number
from utils.ytdl_source import YTDLSource, YTDLError  # type: ignore
from utils.voice_utils import VoiceState, VoiceError  # type: ignore
from utils.song_embed import Song  # type: ignore

from view.player_menu import *  # type: ignore

from view.player_menu import Buttons


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)
        self.voice_states = {}




    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def get_menu_state(self, ctx: commands.Context):
        state = PlayerContext(ctx)
        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

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
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="Вы не в голосовом канале!"), ephemeral=True)
            return

        destination = ctx.author.voice.channel

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
            embed=discord.Embed(description='Volume of the player set to {}%'.format(volume), color=config.COLOR),
            ephemeral=True)

    @commands.hybrid_command(name='now', aliases=['current', 'playing'])
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _now(self, ctx: commands.Context):
        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.hybrid_command(name='pause')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _pause(self, ctx: commands.Context):

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()

    @commands.hybrid_command(name='resume')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _resume(self, ctx: commands.Context):

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()

    @commands.hybrid_command(name='stop')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _stop(self, ctx: commands.Context):

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()

    @commands.hybrid_command(name='skip')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _skip(self, ctx: commands.Context):

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.hybrid_command(name='queue')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing main_page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _shuffle(self, ctx: commands.Context):

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()

    @commands.hybrid_command(name='remove')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _remove(self, ctx: commands.Context, index: int):

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)

    @commands.command(name='loop')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _loop(self, ctx: commands.Context):

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        ctx.voice_state.loop = not ctx.voice_state.loop

    @commands.hybrid_command(name='play')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def _play(self, ctx: commands.Context, *, search: str):

        if ctx.voice_state.voice is None:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)

            except YTDLError as e:
                await ctx.send(embed=discord.Embed(
                    description='An error occurred while processing this request: {}'.format(str(e)),
                    color=discord.Color.red()), ephemeral=True)
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send(embed=discord.Embed(description='Добавлено: {}'.format(str(source)), color=config.COLOR))

    @commands.hybrid_command(name='play_file')
    @app_commands.describe(
        filename='Принимает пути к файлам в формате "path/to/file.webm", файл предварительно должен быть скачен папку'
    )
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def play_file(self, ctx: commands.Context, *, filename: str):

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            await ctx.voice_state._play_file(discord.FFmpegPCMAudio(f'audio_files/{filename}'))

            await ctx.send(
                embed=discord.Embed(description=f'🎶 **Добавлено из файла**: ```{filename}```', color=config.COLOR))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client and ctx.voice_client.is_connected():
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.move_to(ctx.author.voice.channel)

    @commands.hybrid_command(name='menu')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def menu(self, ctx: commands.Context, folder: str):

        channel = ctx.channel
        content = os.listdir(f'./audio_files/{folder}')

        components = []

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        for file in content:
            if len(file) >= 70:
                os.rename(f'./audio_files/{folder}/{file}', f'./audio_files/{folder}/{file[:60]}.webm')
                label = f'{file.split(".")[0][:60]}...'
                custom_id = f'./audio_files/{folder}/{file[:60]}.webm'
            else:
                label = file.split('.')[0]
                custom_id = f'./audio_files/{folder}/{file}'

            components.append({'label': label, 'style': discord.ButtonStyle.green, 'custom_id': custom_id})
            if len(components) == 25:
                button = await channel.send(view=Buttons(ctx, components))
                components.clear()

        components = sorted(
            components,
            key=lambda x: first_number(x['label'])
        )

        archive = discord.Embed(title='Архив', color=config.COLOR)
        player_embed = discord.Embed(title='Сейчас играет 🎶:', color=config.COLOR,
                                     description='```Сейчас ничего не играет :(```')

        ctx.menu_state.music_player = MusicPlayer(ctx, components)

        ctx.menu_state.player = await channel.send(embeds=[archive, player_embed],
                                                   view=Buttons(ctx, ctx.menu_state.music_player))
        ctx.menu_state.menu = await channel.send(view=MenuButtons(ctx, ctx.menu_state.music_player, 50 / 100))


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))