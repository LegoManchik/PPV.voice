import discord
from discord.ext import commands
from discord import app_commands

from discord_bot import config
from discord_bot.data.database import TicketBookingDatabase
from discord_bot.utils.localization import Localization, Language
from discord_bot.utils.logger import BotLogger
from discord_bot.view.booking_settings_view import BookingSettings
from discord_bot.view.ticket_booking_view import StartBookingView


class TicketBooking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)
        self.db = TicketBookingDatabase()

    @commands.hybrid_command(name="buy_ticket", description="Создаёт меню бронирования билетов")
    @app_commands.describe(lang="Язык на котором будет меню")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def buy_ticket(self, ctx: commands.Context, lang: Language):
        await ctx.interaction.response.defer()
        await ctx.channel.send(view=StartBookingView(bot=self.bot, lang=lang.value))

    @commands.hybrid_command(name="cancel_reservation")
    @app_commands.describe(floor="Этаж", seat="Место")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def cancel_reservation(self, ctx: commands.Context, floor: str, seat: str):
        self.db.remove_user(floor=floor, seat=seat)

    @commands.hybrid_command(name="booking_settings")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def booking_settings(self, ctx: commands.Context):
        await ctx.interaction.response.send_message(view=BookingSettings(ctx=ctx), file=discord.File(fp="data/seats.json", filename="seats.json"))

    @commands.hybrid_command(name="setup_database")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def setup_database(self, ctx: commands.Context):
        self.db.generate_seats()
        await ctx.send("Setup")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketBooking(bot))
