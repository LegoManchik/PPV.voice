import os

import asyncio

import discord
from discord.ext import commands

import config
from utils.logger import BotLogger
from database.database import TicketBookingDatabase


class PersistentViewBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.PREFIX, intents=discord.Intents.all(), help_command=None)
        self.persistent_views_added = False

    async def on_ready(self):

        if not self.persistent_views_added:
            self.persistent_views_added = True

        db = TicketBookingDatabase()

        db.__create_tables__()

        logger.info(f'Бот активен как {bot.user} (ID: {bot.user.id})')

        await self.tree.sync()
    
    async def load_extensions(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f'Расширение cogs.{filename[:-3]} загружено')
                except Exception as e:
                    logger.error(f'Не удалось загрузить расширение cogs.{filename[:-3]}: {e}')


if __name__ == "__main__":
    logger = BotLogger().get_logger()
    bot = PersistentViewBot()
    asyncio.run(bot.load_extensions())
    bot.run(config.TOKEN)
