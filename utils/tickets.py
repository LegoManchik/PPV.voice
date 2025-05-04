from datetime import datetime

import discord

import config
from data.database import TicketBookingDatabase
from utils.localization import LangContext


class TicketSystem:
    def __init__(self, bot):
        self.bot = bot

        self.db = TicketBookingDatabase()

    async def create_ticket(self, ctx: LangContext, user: discord.Member, guild: discord.Guild) -> discord.TextChannel:
        ticket_number = await self.db.get_next_ticket_number(guild.id)

        category = discord.utils.get(guild.categories, name="Tickets")
        print(category)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f'ticket-{ctx.lang}-{user.name}-{ticket_number:0>4}',
            category=category,
        )

        everyone = everyone = guild.get_role(config.GUILD_ID)

        await channel.set_permissions(user, read_messages=True, send_messages=False)
        await channel.set_permissions(discord.utils.get(guild.roles, id=config.SUPERVISOR_ROLE_ID), read_messages=True,
                                      send_messages=True)
        await channel.set_permissions(everyone, read_messages=False, send_messages=False)

        self.db.cur.execute('''INSERT INTO tickets 
                     (user_id, channel_id, ticket_number, created_at) 
                     VALUES (?, ?, ?, ?)''', (user.id, channel.id, ticket_number, datetime.now().isoformat()))
        self.db.con.commit()
        self.db.con.close()
        return channel

    async def close_ticket(self, channel):
        self.db.cur.execute('''UPDATE tickets SET status = 'closed' 
                             WHERE channel_id = ?''', (channel.id,))
        self.db.con.commit()
        self.db.con.close()
