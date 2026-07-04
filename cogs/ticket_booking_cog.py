import asyncio
import io
import aiohttp

import discord
from discord.ext import commands
from discord import app_commands, AppCommandType
from discord.utils import get

import config
from data.database import TicketBookingDatabase
from data.json_helper import JsonHelper
from utils.localization import Localization, Language
from utils.logger import BotLogger
from utils.broadcast_helper import send_global_msg, send_global_personal_msg
from utils.ticket_permissions_helper import setup_context_menus
from view.ticket_booking_view import StartBookingView, SEAT_RESERVED_EMBED, StartVIPBookingView
from view.embed import BaseEmbeds


class TicketBooking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = BotLogger().get_discord_cog_logger(self.__cog_name__)

        setup_context_menus(bot)

        self.send_global_msg = app_commands.ContextMenu(
            name='Массовая рассылка',
            callback=send_global_msg,
            type=AppCommandType.message
        )

        self.send_global_personal_msg = app_commands.ContextMenu(
            name='Массовая рассылка в ЛС',
            callback=send_global_personal_msg,
            type=AppCommandType.message
        )

        self.bot.tree.add_command(self.send_global_msg)
        self.bot.tree.add_command(self.send_global_personal_msg)

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
            await ctx.send(embed=BaseEmbeds.success(f"✅ Пользователь {user.mention} теперь будет пинговаться при поступлении новых заявок на бронь"))
        else:
            await ctx.send(embed=BaseEmbeds.error(f"❌ Пользователь {user.mention} уже есть в списке"))

    @commands.hybrid_command(name="remove_ping_user", description="Убрать пользователя из пингов, при заявках")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def remove_ping_user(self, ctx: commands.Context, user: discord.User):
        if JsonHelper.remove_user_in_list(user.id):
            await ctx.send(embed=BaseEmbeds.success(f"✅ Пользователь {user.mention} теперь **НЕ** будет пинговаться при поступлении новых заявок на бронь"))
        else:
            await ctx.send(embed=BaseEmbeds.error(f"❌ Пользователя {user.mention} нет в списке"))

    @commands.hybrid_command(name="manage_all_ticket_perms")
    @app_commands.describe(action="Выберите действие: выдать или отобрать права")
    @app_commands.choices(action=[
        app_commands.Choice(name="✅ Выдать права", value="grant"),
        app_commands.Choice(name="🔒 Отобрать права", value="revoke")
    ])
    @commands.has_permissions(administrator=True)
    async def manage_all_ticket_perms(self, ctx: commands.Context, action: str):
        await ctx.defer()

        action = action.lower()
        category = get(ctx.guild.categories, id=config.TICKETS_CATEGORY_ID)
        if not category:
            await ctx.send(embed=BaseEmbeds.error("❌ Категория тикетов не найдена!"))
            return

        tickets = list(category.channels)
        if not tickets:
            await ctx.send(embed=BaseEmbeds.info("ℹ️ Нет тикетов для обработки!"))
            return

        action_name = "выдачу" if action == "grant" else "отзыв"
        progress_msg = await ctx.send(embed=discord.Embed(
            description=f"🔄 Начинаю {action_name} прав в {len(tickets)} тикетах...",
            color=discord.Color.blue()
        ))

        database = TicketBookingDatabase()
        semaphore = asyncio.Semaphore(10)
        results = {"success": 0, "failed": 0, "no_user": 0}

        async def process_ticket(channel):
            async with semaphore:
                ticket = database.get_ticket_by_channel(channel.id)

                if ticket is not None:
                    user = ctx.guild.get_member(ticket.get("user_id"))
                else:
                    try:
                        user_name = channel.name.split("-")[2]
                        user = get(ctx.guild.members, name=user_name)
                    except:
                        user = None

                if user:
                    try:
                        overwrite = channel.overwrites_for(user)

                        if action == "grant":
                            overwrite.send_messages = True
                            action_text = "выданы"
                        else:
                            overwrite.send_messages = False
                            action_text = "отозваны"

                        await channel.set_permissions(user, overwrite=overwrite)
                        await channel.send(f"{"✏️" if overwrite.send_messages else "🔒"} Пользователю {user.mention} теперь **{"разрешено" if overwrite.send_messages else "запрещено"}** писать в {channel.mention}")
                        self.logger.info(f"✅ Права {action_text} для {user.name} в {channel.name}")
                        return True
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка для {channel.name}: {e}")
                        return False
                return None

        tasks = [process_ticket(channel) for channel in tickets]
        results_list = await asyncio.gather(*tasks)

        for result in results_list:
            if result is True:
                results["success"] += 1
            elif result is False:
                results["failed"] += 1
            else:
                results["no_user"] += 1

        embed = discord.Embed(
            title=f"Обновление прав завершено!",
            description=f"📨 Обработано прав: {results['success']}\n"
                        f"❌ Ошибок: {results['failed']}\n"
                        f"👤 Пользователь не найден: {results['no_user']}",
            color=config.COLOR
        )
        await progress_msg.edit(content=None, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketBooking(bot))
