import asyncio
import logging

from aiogram import Dispatcher, Bot, Router, types
from aiogram.fsm.storage.memory import MemoryStorage

import config

from tg_handlers import get_handlers_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router(name="bot")


class BotCore:
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        self.dp.include_router(get_handlers_router())

    async def run(self):
        await self.dp.start_polling(self.bot)


if __name__ == '__main__':
    bot = BotCore(config.TG_TOKEN)

    asyncio.run(bot.run())

