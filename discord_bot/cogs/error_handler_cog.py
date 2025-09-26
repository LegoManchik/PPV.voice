import discord.errors
import traceback

from discord.ext import commands

from discord_bot.utils.logger import BotLogger


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_logger()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: discord.errors.Any):
        error = getattr(error, 'original', error)

        self.logger.error(f"Ошибка в команде {ctx.command}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
