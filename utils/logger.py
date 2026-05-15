import datetime
import logging

import asyncio
import logging
import datetime
import os
import traceback
from functools import wraps
from logging.handlers import RotatingFileHandler
import discord
from discord.ext import commands


def interaction_error_handler(logger: logging.Logger):

    def decorator(func):

        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            logger.info(f"{interaction.user} нажал на {interaction.data.get('custom_id')}")
            try:
                return await func(self, interaction, *args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {interaction.data.get('custom_id')}: {e}")
                traceback.print_exc()
        return wrapper
    return decorator


class BotLogger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)

        self.logger = logging.getLogger("PPV")
        self.logger.setLevel(logging.INFO)

        self.logger.handlers.clear()

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S'
        )

        file_handler = RotatingFileHandler(
            filename=f"logs/bots-{datetime.datetime.now().strftime('%d-%m-%Y')}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        error_handler = RotatingFileHandler(
            filename=f"logs/errors-{datetime.datetime.now().strftime('%d-%m-%Y')}.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

        self.discord_logger = logging.getLogger("PPV.Discord")

        self.discord_loggers = {}
        self.file_loggers = {}

        self.discord_logger.setLevel(logging.INFO)

        self.discord_logger.propagate = True

    def get_discord_logger(self) -> logging.Logger:
        return self.discord_logger

    def get_main_logger(self) -> logging.Logger:
        return self.logger

    def get_discord_cog_logger(self, cog_name: str) -> logging.Logger:
        if cog_name not in self.discord_loggers:
            logger = logging.getLogger(f"PPV.Discord.Сog.{cog_name}")
            logger.propagate = True
            self.discord_loggers[cog_name] = logger
        return self.discord_loggers[cog_name]

    def get_file_logger(self, name: str) -> logging.Logger:
        if name not in self.file_loggers:
            logger = logging.getLogger(f"PPV.{name}")
            logger.propagate = True
            self.file_loggers[name] = logger
        return self.file_loggers[name]

