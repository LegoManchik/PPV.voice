import asyncio

import discord

from discord import app_commands
from discord.ext import commands
from discord.utils import get

import config
from data.database import TicketBookingDatabase
from utils.logger import BotLogger
from utils.tickets import TicketSystem


class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)

    @commands.hybrid_command(name="clear_tickets")
    @commands.has_permissions(administrator=True)
    async def clear_tickets(self, ctx: commands.Context):
        await ctx.send(embed=discord.Embed(description="🗑️ Начинаю массовое удаление тикетов...", color=discord.Color.blue()), ephemeral=True)

        category = get(ctx.guild.categories, id=config.TICKETS_CATEGORY_ID)
        if not category:
            await ctx.send(embed=discord.Embed(description="❌ Категория тикетов не найдена!", color=discord.Color.blue()), ephemeral=True)
            return

        tickets = category.channels
        if not tickets:
            await ctx.send(embed=discord.Embed(description="ℹ️ Нет тикетов для удаления!", color=discord.Color.blue()), ephemeral=True)
            return

        tickets_data = TicketSystem(self.bot)
        database = TicketBookingDatabase()

        semaphore = asyncio.Semaphore(5)
        results = {"success": 0, "failed": 0}

        async def delete_ticket(channel):
            async with semaphore:
                try:
                    if database.get_ticket_by_channel(channel.id) is not None:
                        await tickets_data.close_ticket(channel)
                    await channel.delete()
                    results["success"] += 1
                    self.logger.info(f"✅ Удалён тикет: {channel.name}")
                except Exception as e:
                    results["failed"] += 1
                    self.logger.error(f"❌ Ошибка при удалении {channel.name}: {e}")

        tasks = [delete_ticket(channel) for channel in tickets]
        await asyncio.gather(*tasks)

        await ctx.send(embed=discord.Embed(
            description=
                       f"✅ **Удаление завершено!**\n"
                       f"📨 Успешно: {results['success']}\n"
                       f"❌ Ошибок: {results['failed']}", color=discord.Color.blue()),
                       ephemeral=True,
                       delete_after=10
        )

    @commands.hybrid_command(name="setup_database")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def setup_database(self, ctx: commands.Context):
        self.db.generate_seats()
        await ctx.send("Setup")

async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
