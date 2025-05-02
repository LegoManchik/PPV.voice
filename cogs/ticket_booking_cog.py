import enum

from discord import app_commands
from discord.ext import commands

from view.ticket_booking_view import BookingTicketButton, ConfirmationButton
from data.database import TicketBookingDatabase
from utils.localization import LangContext


class Language(enum.Enum):
    RU = "ru"
    EN = "en"


class Floor(enum.Enum):
    FLOOR_1 = 1
    FLOOR_2 = 2
    FLOOR_3 = 3


class TicketBooking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.db = TicketBookingDatabase()

    @commands.hybrid_command(name="buy_ticket", description="Создаёт меню бронирования билетов")
    @commands.has_permissions(manage_guild=True)
    async def buy_ticket(self, ctx: commands.Context, lang: Language):

        await ctx.send('Booking Ticket', view=ConfirmationButton(bot=self.bot, lang=lang.value))

    @commands.hybrid_command(name="cancel_reservation", description="Создаёт меню бронирования билетов", displayed_name="отменить бронирование")
    @commands.has_permissions(manage_guild=True)
    async def cancel_reservation(self, ctx, floor: Floor, seat: str):
        self.db.remove_user(floor=floor.value, seat=seat)

    @commands.hybrid_command(name="setup_database")
    @commands.has_permissions(manage_guild=True)
    async def setup_database(self, ctx: commands.Context):
        self.db.generate_seats()
        await ctx.send("Setup")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketBooking(bot))
