import os
import sys

import discord
from discord.ext import commands


class Commands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name='restart')
    @commands.has_permissions(manage_guild=True)
    async def restart(self, ctx):

        embed = discord.Embed(
            title='Перезапуск бота',
            color=0x1abc9c
        )
        await ctx.send(embed=embed)
        python = sys.executable
        os.execl(python, python, *sys.argv)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))