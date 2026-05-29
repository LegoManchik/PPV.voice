import asyncio
import aiohttp
import io
import discord
from discord.utils import get

import config
from data.database import TicketBookingDatabase
from utils.decorators import is_moderator
from utils.logger import BotLogger

logger = BotLogger().get_file_logger(__name__)


async def prepare_files_data(message: discord.Message) -> list:
    files_data = []

    for attachment in message.attachments:
        if attachment.size == 0:
            continue

        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    file_data = await resp.read()
                    if len(file_data) > 0:
                        files_data.append({
                            'data': bytearray(file_data),
                            'filename': attachment.filename,
                            'spoiler': attachment.is_spoiler()
                        })
                    else:
                        logger.warn(f"⚠️ Файл {attachment.filename} скачан, но имеет 0 байт")

    return files_data


async def get_user_from_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    database = TicketBookingDatabase()
    ticket = database.get_ticket_by_channel(channel.id)

    if ticket is not None:
        return interaction.guild.get_member(ticket.get("user_id"))
    else:
        return get(interaction.guild.members, name=channel.name.split("-")[2])


async def send_to_single_recipient(channel, user, content, embeds, files_data):
    try:
        files = []
        for fd in files_data:
            files.append(discord.File(
                fp=io.BytesIO(fd['data'].copy()),
                filename=fd['filename'],
                spoiler=fd['spoiler']
            ))

        await channel.send(content=content, embeds=embeds, files=files if files else None)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в {channel.name}: {e}")
        return False



async def broadcast_parallel(interaction: discord.Interaction, message: discord.Message, target: str):
    category = get(interaction.guild.categories, id=config.TICKETS_CATEGORY_ID)
    database = TicketBookingDatabase()

    files_data = await prepare_files_data(message)

    recipients = []
    for channel in category.channels:
        user = await get_user_from_channel(interaction, channel)
        if not user:
            continue

        content = message.content.format(user=user.mention) if message.content else ""

        if target == "channel":
            recipients.append((channel, user, content))
        else:
            recipients.append((user, user, content))

    if not recipients:
        await interaction.response.send_message(
           embed=discord.Embed(description="❌ Нет получателей для рассылки!", color=discord.Color.red()), ephemeral=True)
        return

    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"📤 Начинаю рассылку {len(recipients)} получателям...",
            color=discord.Color.blue()
        ),
        ephemeral=True
    )

    semaphore = asyncio.Semaphore(10)

    async def send_with_limit(recipient):
        async with semaphore:
            target_obj, user, content = recipient
            return await send_to_single_recipient(target_obj, user, content, message.embeds, files_data)

    tasks = [send_with_limit(r) for r in recipients]
    results = await asyncio.gather(*tasks)

    success = sum(results)
    failed = len(results) - success

    target_name = "тикеты" if target == "channel" else "ЛС"
    await interaction.edit_original_response(
        embed=discord.Embed(
            description=f"✅ **Рассылка в {target_name} завершена!**\n📨 Отправлено: {success}/{len(recipients)}\n❌ Ошибок: {failed}",
            color=discord.Color.green()
        )
    )


@is_moderator
async def send_global_msg(interaction: discord.Interaction, message: discord.Message):
    await broadcast_parallel(interaction, message, target="channel")


@is_moderator
async def send_global_personal_msg(interaction: discord.Interaction, message: discord.Message):
    await broadcast_parallel(interaction, message, target="user")
