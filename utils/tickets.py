from datetime import datetime

import discord
from discord.utils import get

import config
from data.database import TicketBookingDatabase
from data.extract_json import JsonExtract
from utils.localization import LangContext


class TicketSystem:
    def __init__(self, bot):
        self.bot = bot

        self.db = TicketBookingDatabase()

    async def create_ticket(self, ctx: LangContext, user: discord.Member, guild: discord.Guild) -> discord.TextChannel:
        ticket_number = JsonExtract.get_random_number()
        JsonExtract.add_number(ticket_number)

        role = get(guild.roles, id=config.SUPERVISOR_ROLE_ID)

        category = discord.utils.get(guild.categories, id=config.TICKETS_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f'ticket-{ctx.lang}-{user.name}-{ticket_number:0>5}',
            category=category,
            overwrites=overwrites
        )

        self.db.cur.execute('''INSERT INTO tickets 
                     (user_id, channel_id, ticket_number, created_at) 
                     VALUES (?, ?, ?, ?)''', (user.id, channel.id, ticket_number, datetime.now().isoformat()))

        self.db.con.commit()
        return channel

    async def close_ticket(self, channel):
        self.db.cur.execute('''UPDATE tickets SET status = 'closed' 
                             WHERE channel_id = ?''', (channel.id,))
        self.db.con.commit()
        self.db.con.close()
