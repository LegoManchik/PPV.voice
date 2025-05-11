import discord.ui
from discord.utils import get

import config


class LimitedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @classmethod
    def is_moderator(cls, user: discord.Member):
        return get(user.roles, id=config.SUPERVISOR_ROLE_ID) is not None or get(user.roles, id=config.OPERATOR_ROLE_ID) is not None
