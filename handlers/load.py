import os

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

import config
from utils.logger import BotLogger
from utils.command_filters import UserIdFilter

router = Router(name="load")

logger = BotLogger().get_telegram_handler_logger(router.name)


@router.message(UserIdFilter(config.TG_ADMINS), Command(commands=["load", "download", "l"]))
async def load_handler(message: types.Message):
    message_content = message.audio if message.audio is not None else message.document

    file = await message.bot.get_file(message_content.file_id)

    folder = message.caption.split(' ')[-1]

    if len(message.caption.split(' ')) > 1 and folder != '':
        if not os.path.exists(f"audio_files/{folder}"):
            os.makedirs(f"audio_files/{folder}")

        save_path = f"audio_files/{folder}/{message_content.file_name}"
    else:
        save_path = f"audio_files/{message_content.file_name}"

    await message.bot.download_file(file.file_path, save_path)

    logger.info(f"{message.from_user.full_name} (ID:{message.from_user.id}) воспользовался командой '/{router.name}'")
    logger.info(f"Аудио файл сохранён по пути: {save_path}")
    await message.answer(f"> Аудио файл загружен и сохранён по пути:\n`{save_path}`", parse_mode=ParseMode.MARKDOWN_V2)
