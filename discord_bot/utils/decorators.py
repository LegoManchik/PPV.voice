from functools import wraps

import discord
from discord.ext import commands
from discord.utils import get

from discord_bot import config


def is_moderator(func):
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        if get(interaction.user.roles, id=config.SUPERVISOR_ROLE_ID) is not None or get(interaction.user.roles, id=config.OPERATOR_ROLE_ID) is not None:
            return await func(self, interaction, *args, **kwargs)
        else:
            await interaction.response.defer()

    return wrapper

