import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get

import config
from data.database import TicketBookingDatabase
from data.json_helper import JsonHelper
from utils.localization import Localization, Language
from utils.logger import BotLogger
from view.ticket_booking_view import StartBookingView, SEAT_RESERVED_EMBED, StartVIPBookingView


class TicketBooking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)
        self.db = TicketBookingDatabase()

    @commands.hybrid_command(name="buy_ticket", description="Создаёт меню бронирования билетов")
    @app_commands.describe(lang="Язык на котором будет меню")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def buy_ticket(self, ctx: commands.Context, lang: Language):
        await ctx.channel.send(view=StartBookingView(bot=self.bot, lang=lang.value))
        await ctx.interaction.response.defer()

    @commands.hybrid_command(name="buy_vip", description="Создаёт меню бронирования vip билетов")
    @app_commands.describe(lang="Язык на котором будет меню")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def buy_vip(self, ctx: commands.Context, lang: Language):
        await ctx.channel.send(view=StartVIPBookingView(bot=self.bot, lang=lang.value))
        await ctx.interaction.response.defer()

    @commands.hybrid_command(name="approve_message")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def approve_message(self, ctx: commands.Context, user: discord.User, lang: Language):
        tickets = get(ctx.channel.guild.categories, id=config.TICKETS_CATEGORY_ID).channels

        for ticket in tickets:
            if user.name in ticket.name.split("-")[2]:
                await ticket.send(user.mention, embed=Localization.translatable_embed(SEAT_RESERVED_EMBED, key="embed.seat_reserved", lang=lang.value))

        await ctx.interaction.response.defer()

    @commands.hybrid_command(name="add_ping_user", description="Добавить пользователь я в пинг, при заявках")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def add_ping_user(self, ctx: commands.Context, user: discord.User):
        if JsonHelper.add_user_in_list(user.id):
            await ctx.send(embed=discord.Embed(description=f"✅ Пользователь {user.mention} теперь будет пинговаться при поступлении новых заявок на бронь"))
        else:
            await ctx.send(embed=discord.Embed(description=f"❌ Пользователь {user.mention} уже есть в списке"))

    @commands.hybrid_command(name="remove_ping_user", description="Убрать пользователя из пингов, при заявках")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def remove_ping_user(self, ctx: commands.Context, user: discord.User):
        if JsonHelper.remove_user_in_list(user.id):
            await ctx.send(embed=discord.Embed(description=f"✅ Пользователь {user.mention} теперь **НЕ** будет пинговаться при поступлении новых заявок на бронь"))
        else:
            await ctx.send(embed=discord.Embed(description=f"❌ Пользователя {user.mention} нет в списке"))


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketBooking(bot))
