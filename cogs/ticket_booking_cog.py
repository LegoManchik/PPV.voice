import enum


from discord.ext import commands

from view.ticket_booking_view import BookingTicketButton
from database.database import TicketBookingDatabase


class Language(enum.Enum):
    RU = "ru"
    EN = "en"


class TicketBooking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="buy_ticket")
    @commands.has_permissions(manage_guild=True)
    async def buy_ticket(self, ctx: commands.Context, lang: Language):
        await ctx.send('Booking Ticket', view=BookingTicketButton(ctx, lang=lang.value))

    @commands.hybrid_command(name="setup_database")
    @commands.has_permissions(manage_guild=True)
    async def setup_database(self, ctx: commands.Context):
        db = TicketBookingDatabase()
        db.generate_seats()
        await ctx.send("Setup")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketBooking(bot))