
import discord
from discord import app_commands, AppCommandType, AppCommandContext
from discord.utils import get

import config

from data.database import TicketBookingDatabase
from utils.decorators import is_moderator
from utils.logger import BotLogger

logger = BotLogger().get_file_logger(__name__)


@is_moderator
async def toggle_chat(interaction: discord.Interaction, user: discord.User):
    db = TicketBookingDatabase()
    if not db.get_ticket_by_channel(interaction.channel.id):
        await interaction.response.send_message(embed=discord.Embed(description="❌ Только в тикете!", color=discord.Color.blue()), ephemeral=True, delete_after=3)
        return

    current_perms = interaction.channel.overwrites_for(user)

    if current_perms.send_messages is True:
        new_overwrite = discord.PermissionOverwrite(
            send_messages=False,
            read_messages=True
        )
        action = "запрещено"
        emoji = "🔒"
    else:
        new_overwrite = discord.PermissionOverwrite(
            send_messages=True,
            read_messages=True
        )
        action = "разрешено"
        emoji = "✏️"

    member = get(interaction.guild.members, id=user.id)
    await interaction.channel.set_permissions(member, overwrite=new_overwrite)

    await interaction.response.send_message(
        f"{emoji} Пользователю {user.mention} теперь **{action}** писать в {interaction.channel.mention}"
    )


def setup_context_menus(bot):

    bot.tree.add_command(
        app_commands.ContextMenu(
            name='✍ Разрешить/Запретить писать',
            callback=toggle_chat,
            type=AppCommandType.user
        )
    )
