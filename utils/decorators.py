from functools import wraps

import discord
from discord.ext import commands
from discord.utils import get

import config

from view.embed import BaseEmbeds


def is_moderator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        interaction = None

        if len(args) > 0:
            if hasattr(args[0], 'user') and hasattr(args[0].user, 'roles'):
                interaction = args[0]
            elif len(args) > 1 and hasattr(args[1], 'user'):
                interaction = args[1]

        if interaction is None and 'interaction' in kwargs:
            interaction = kwargs['interaction']

        if interaction is None:
            return await func(*args, **kwargs)

        user_roles = interaction.user.roles
        supervisor_role = get(interaction.guild.roles, id=config.SUPERVISOR_ROLE_ID)
        operator_role = get(interaction.guild.roles, id=config.OPERATOR_ROLE_ID)

        if supervisor_role in user_roles or operator_role in user_roles:
            return await func(*args, **kwargs)
        else:
            await interaction.response.send_message(
                embed=BaseEmbeds.error("❌ У вас нет прав для выполнения этой команды!"),
                ephemeral=True
            )
            return

    return wrapper