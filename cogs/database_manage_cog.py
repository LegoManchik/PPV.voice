from discord.ext import commands

import config
from utils.logger import BotLogger
from view.ticket_database_view import DatabaseMenuView


class DatabaseManage(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)

    @commands.hybrid_command(name="database")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def database(self, ctx: commands.Context):
        await ctx.send(view=DatabaseMenuView())


async def setup(bot: commands.Bot):
    await bot.add_cog(DatabaseManage(bot))
