import os

import discord
from discord.ext import commands
from pytube import Playlist


import config
from utils.sort_utils import first_number
from utils.ytdl_source import YTDLSource
from view.file_manager_view import MkDirButtons
from view.file_manager_view import get_filelist_embed


class FileManage(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name='download')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def download(self, ctx: commands.Context, folder: str, url: str = None, file: discord.Attachment = None):
        
        if not(folder in os.listdir('./audio_files')):
            os.mkdir(f'audio_files/{folder}')

        await ctx.interaction.response.send_message(embed=discord.Embed(title='Скаченные файлы:', color=config.COLOR), ephemeral=True)

        text = ''

        if url is not None:
            if 'list=' in url:
                playlist = Playlist(url)
                urls = playlist.video_urls  

                for song_url in urls:
                    filename = YTDLSource.download(url=song_url, folder=folder)
                    text += f'```{filename}```\n'

                    await ctx.interaction.edit_original_response(embed=discord.Embed(title='Скаченные файлы:', description=text, color=config.COLOR))
            else:
                filename = YTDLSource.download(url=url, folder=folder)
                text = f'```{filename}```'

        elif file is not None:
            if not(file in os.listdir(f"./audio_files/{folder}")):
                text += f'```{file.filename}```\n'
                file_path = os.path.join('audio_files', folder, file.filename)
                await file.save(file_path)

        embed = discord.Embed(title='Скаченные файлы:', 
                              description=text, color=config.COLOR).set_footer(text='Все файлы скачены')
        await ctx.interaction.edit_original_response(embed=embed)

        for file in os.listdir(f"./audio_files/{folder}"):
            if len(file) >= 70:
                os.rename(f"./audio_files/{folder}/{file}", file[:60] + ".{}".format(file.split('.')[1]))

    @commands.hybrid_command(name='explorer')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def explorer(self, ctx: commands.Context):
        message = await ctx.send(embed=get_filelist_embed(os.listdir('./audio_files')))
        await message.edit(view=MkDirButtons(message))


async def setup(bot: commands.Bot):
    await bot.add_cog(FileManage(bot))
