from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

import config
from utils.command_filters import UserIdFilter
from utils.logger import BotLogger


router = Router(name="start")

logger = BotLogger().get_telegram_handler_logger(router.name)


@router.message(UserIdFilter(config.TG_ADMINS), CommandStart())
async def start_handler(message: types.Message):
    text = """
<blockquote><b>Привет, я PPV bot!</b></blockquote>
Для загрузки музыки в <b>PPV.voice</b> можете использовать команды: <code>/l</code>, <code>/load</code>, <code>/download</code>
Всё просто, прикрепите аудио файл <i>( желательно <code>mp3</code> )</i>
и напишите например:
<code>/load &lt;название папки&gt;</code>
"""
    logger.info(f"{message.from_user.full_name} (ID:{message.from_user.id}) воспользовался командой '/{router.name}'")
    await message.answer(text=text, parse_mode=ParseMode.HTML)







