import json
import logging
import os

import asyncio
import traceback
from inspect import Traceback

from dotenv import load_dotenv

import discord
from discord.ext import commands

import config
from data.json_helper import JsonHelper
from data.seats_debug import SeatsDebug
from utils.localization import LangContext
from view.ticket_booking_view import StartBookingView, StartBookingButton

from data.database import TicketBookingDatabase
from utils.logger import BotLogger

logger_manager = BotLogger()
main_logger = logger_manager.get_main_logger()
discord_logger = logger_manager.get_discord_logger()

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

        self.setup()
        await self.tree.sync()

    @staticmethod
    def setup():
        database = TicketBookingDatabase()

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
                    discord_logger.info(f'✅ Расширение cogs.{filename[:-3]} загружено')
                except Exception as e:
                    discord_logger.error(f'❌ Не удалось загрузить расширение cogs.{filename[:-3]}: {e}')
                    traceback.print_exc()


discord_bot = DiscordBot()


async def run_discord_bot():
    try:
        await discord_bot.start(str(os.getenv("DS_TOKEN")))
    except Exception as e:
        discord_logger.error(f"Ошибка Discord бота: {e}")
    finally:
        await discord_bot.close()


async def main():
    discord_task = asyncio.create_task(run_discord_bot())

    await asyncio.gather(discord_task, discord_bot.load_extensions(), SeatsDebug.test())

if __name__ == "__main__":
    asyncio.run(main())
