from discord.ext import commands

import config
from view.ticket_database_view import DatabaseMenuEmbed, DatabaseMenuButtons


class DatabaseManage(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="database")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def database(self, ctx: commands.Context):
        embeds = DatabaseMenuEmbed(floor=1).get_seat_list()
        await ctx.send(embeds=embeds, view=DatabaseMenuButtons(floor=1))


async def setup(bot: commands.Bot):
    await bot.add_cog(DatabaseManage(bot))
