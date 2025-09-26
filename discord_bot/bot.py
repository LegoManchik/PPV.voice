import json
import logging
import os

import asyncio
from dotenv import load_dotenv

import discord
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from discord.ext import commands

from discord_bot import config
from discord_bot.utils.localization import LangContext
from discord_bot.view.ticket_booking_view import StartBookingView, StartBookingButton
from handlers import get_handlers_router

from data.database import TicketBookingDatabase
from utils.logger import BotLogger

logger_manager = BotLogger()
main_logger = logger_manager.get_main_logger()
discord_logger = logger_manager.get_discord_logger()
telegram_logger = logger_manager.get_telegram_logger()

load_dotenv('./.env')


class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.PREFIX, intents=discord.Intents.all(), help_command=None)
        self.persistent_views_added = False

    async def on_ready(self):

        if not self.persistent_views_added:
            self.persistent_views_added = True

            self.add_view(view=StartBookingView(self, lang='en'))
            self.add_view(view=StartBookingView(self, lang='ru'))

        discord_logger.info(f'Discord bot {self.user} активен (ID: {self.user.id})')

        self.__setup__()
        await self.tree.sync()

    @staticmethod
    def __setup__():
        database = TicketBookingDatabase()
        database.create_tables()
        database.generate_seats()

        if not "tickets.json" in os.listdir("data"):
            with open("data/tickets.json", "w", encoding="utf-8") as file:
                json.dump([], file, indent=4)

        if not "ping_users.json" in os.listdir("data"):
            with open("data/ping_users.json", "w", encoding="utf-8") as file:
                json.dump([], file, indent=4)

    async def load_extensions(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    discord_logger.info(f'Расширение cogs.{filename[:-3]} загружено')
                except Exception as e:
                    discord_logger.error(f'Не удалось загрузить расширение cogs.{filename[:-3]}: {e}')


class TelegramBot:
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        self.dp.include_router(get_handlers_router())

    async def start(self):
        await self.dp.start_polling(self.bot)


discord_bot = DiscordBot()
telegram_bot = TelegramBot(os.getenv("TG_TOKEN"))


async def run_discord_bot():
    try:
        await discord_bot.start(os.getenv("DS_TOKEN"))
    except Exception as e:
        discord_logger.error(f"Ошибка Discord бота: {e}")
    finally:
        await discord_bot.close()


async def run_telegram_bot():
    try:
        me = await telegram_bot.bot.get_me()
        telegram_logger.info(f"Telegram bot {me.first_name} активен (ID:{telegram_bot.bot.id})")
        await telegram_bot.start()
    except Exception as e:
        telegram_logger.error(f"Ошибка Telegram бота: {e}")


async def main():

    discord_task = asyncio.create_task(run_discord_bot())
    telegram_task = asyncio.create_task(run_telegram_bot())

    await asyncio.gather(discord_task, telegram_task, discord_bot.load_extensions())

if __name__ == "__main__":
    asyncio.run(main())
