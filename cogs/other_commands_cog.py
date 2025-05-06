import os
import sys

import discord
from discord.ext import commands

import config

RESTART_EMBED = discord.Embed(title='Перезапуск бота', color=0x1abc9c)


class Commands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name='restart')
    @commands.has_permissions(manage_guild=True)
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def restart(self, ctx):
        await ctx.send(embed=RESTART_EMBED)
        python = sys.executable
        os.execl(python, python, *sys.argv)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
