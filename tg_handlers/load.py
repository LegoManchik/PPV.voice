import os

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

router = Router(name="load")


@router.message(Command(commands=["load", "download", "l"]))
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

    await message.answer(f"> Аудио файл загружен и сохранён по пути:\n`{save_path}`", parse_mode=ParseMode.MARKDOWN_V2)
