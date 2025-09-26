from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

from discord_bot import config
from discord_bot.utils.command_filters import UserIdFilter

router = Router(name="start")


@router.message(UserIdFilter(config.TG_ADMINS), CommandStart())
async def start_handler(message: types.Message):
    text = """
<blockquote><b>Привет, я PPV bot!</b></blockquote>
Для загрузки музыки в <b>PPV.voice</b> можете использовать команды: <code>/l</code>, <code>/load</code>, <code>/download</code>
Всё просто, прикрепите аудио файл <i>( желательно <code>mp3</code> )</i>
и напишите например:
<code>/load &lt;название папки&gt;</code>
"""
    await message.answer(text=text, parse_mode=ParseMode.HTML)







