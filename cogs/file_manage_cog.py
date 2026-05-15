import os

import discord
from discord.ext import commands

import config
from utils.logger import BotLogger
from view.file_manager_view import get_filelist_embed, MkDirButtons


class FileManage(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)

    @commands.hybrid_command(name='explorer')
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def explorer(self, ctx: commands.Context):
        message = await ctx.send(embed=get_filelist_embed(os.listdir('./audio_files')))
        await message.edit(view=MkDirButtons(message))


async def setup(bot: commands.Bot):
    await bot.add_cog(FileManage(bot))
