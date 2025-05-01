
from discord.ext import commands


class PlayerMenu:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.channel = None
        self.buttons = []
        self.volume_menu = None

    async def edit(self):
        await self.volume_menu.edit(self._ctx.voice_state._volume)