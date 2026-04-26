import asyncio

import discord

from discord import app_commands
from discord.ext import commands
from discord.utils import get

import config
from utils.tickets import TicketSystem


class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="clear_tickets")
    @commands.has_permissions(administrator=True)
    async def clear_tickets(self, ctx: commands.Context):
        tickets_data = TicketSystem(self.bot)
        for channel in get(ctx.guild.categories, id=config.TICKETS_CATEGORY_ID).channels:
            await tickets_data.close_ticket(channel)
            await channel.delete()
            await asyncio.sleep(2)

    @commands.hybrid_command(name="setup_database")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def setup_database(self, ctx: commands.Context):
        self.db.generate_seats()
        await ctx.send("Setup")


async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
