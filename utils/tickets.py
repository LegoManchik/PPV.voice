from datetime import datetime

import discord
from discord.utils import get
from discord.ext.commands import Context

import config
from data.database import TicketBookingDatabase
from data.json_helper import JsonHelper


class TicketSystem:
    def __init__(self, bot):
        self.bot = bot

        self.database = TicketBookingDatabase()

    async def create_ticket(self, lang: str, user: discord.Member, guild: discord.Guild) -> discord.TextChannel:
        ticket_number = JsonHelper.get_random_number()
        JsonHelper.add_number(ticket_number)

        role = get(guild.roles, id=config.SUPERVISOR_ROLE_ID)

        category = discord.utils.get(guild.categories, id=config.TICKETS_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f'ticket-{lang}-{user.name}-{ticket_number:0>5}',
            category=category,
            overwrites=overwrites
        )
        with self.database.database.get_cursor() as cursor:
            cursor.execute('''INSERT INTO tickets 
                         (user_id, channel_id, ticket_number, created_at) 
                         VALUES (?, ?, ?, ?)''', (user.id, channel.id, ticket_number, datetime.now().isoformat()))

        return channel

    async def close_ticket(self, channel: discord.TextChannel):
        with self.database.database.get_cursor() as cursor:
            cursor.execute('''UPDATE tickets SET status = 'closed' WHERE channel_id = ?''', (channel.id,))
