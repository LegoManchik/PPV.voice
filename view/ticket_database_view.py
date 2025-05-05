import asyncio

import discord
from discord.ext import commands
from discord.ui import Select

import config
from data.database import TicketBookingDatabase


class DatabaseMenuEmbed:
    def __init__(self, floor=1):
        self.db = TicketBookingDatabase()

        self.floor = floor

    def get_seat_list(self) -> list:
        embeds = []
        embed = discord.Embed(title=f"Этаж {self.floor}")
        embed.set_image(url='https://cdn.discordapp.com/attachments/1260875649866797058/1369025457055600750/invisible_line.png')

        embed.add_field(name="Место", value="", inline=True)
        embed.add_field(name="USER_ID", value="", inline=True)
        embed.add_field(name="ИГРОКИ", value="", inline=True)

        for seat in self.db.get_seat_list(self.floor):
            user = f"<@{seat[1]}>"
            if seat[1] is None:
                user = f"<@&{config.NONE_ROLE_ID}>"

            embed.add_field(name="", value=f"```{seat[0]}```", inline=True)
            embed.add_field(name="", value=user, inline=True)
            embed.add_field(name="", value=f"```{seat[2]}```", inline=True)
            if len(embed.fields) == 21:
                embeds.append(embed)
                embed = discord.Embed()
                embed.set_image(url='https://cdn.discordapp.com/attachments/1260875649866797058/1369025457055600750/invisible_line.png')

        embeds.append(embed)

        return embeds


class DatabaseMenuButtons(discord.ui.View):
    def __init__(self, floor: int = 1):
        super().__init__(timeout=None)

        self.floor = floor

        back_button = discord.ui.Button(emoji="⬅", style=discord.ButtonStyle.gray, custom_id="database_menu_back", disabled=floor==1)
        next_button = discord.ui.Button(emoji="➡", style=discord.ButtonStyle.gray, custom_id="database_menu_next", disabled=floor==3)

        cancel_reservetion_button = discord.ui.Button(label="Отменить бронь", emoji="🚩", style=discord.ButtonStyle.gray, custom_id="database_menu_cancel_reservetion")

        back_button.callback = self.back_callback
        next_button.callback = self.next_callback
        cancel_reservetion_button.callback = self.cancel_reservetion_callback

        self.add_item(back_button)
        self.add_item(next_button)
        self.add_item(cancel_reservetion_button)

    async def back_callback(self, interaction: discord.Interaction):
        embeds = DatabaseMenuEmbed(self.floor - 1).get_seat_list()
        await interaction.response.edit_message(embeds=embeds, view=DatabaseMenuButtons(self.floor-1))

    async def next_callback(self, interaction: discord.Interaction):
        embeds = DatabaseMenuEmbed(self.floor + 1).get_seat_list()
        await interaction.response.edit_message(embeds=embeds, view=DatabaseMenuButtons(self.floor+1))

    async def cancel_reservetion_callback(self, interactrion: discord.Interaction):
        await interactrion.response.send_message(view=SeatSelectView(interactrion.message, floor=self.floor), ephemeral=True)


class DatabaseMenuSeatSelect(discord.ui.Select):
    def __init__(self, message, floor: int):
        options = []

        self.db = TicketBookingDatabase()

        self.floor = floor

        self.message = message

        for seat in self.db.get_seat_list(floor):
            emoji = ""
            if seat[1] is None:
                emoji = "⚫"
            else:
                emoji = "🔵"

            options.append(
                discord.SelectOption(
                    label=seat[0],
                    value=seat[0],
                    description=f"{seat[1]} | {seat[2]}",
                    emoji=emoji
                )
            )

        super().__init__(
            custom_id='seat_select',
            placeholder="Выберите место",
            options=options
        )

    async def callback(self, inter: discord.MessageInteraction):
        self.db.remove_user(self.floor, self.values[0])

        await asyncio.sleep(3)

        embed = DatabaseMenuEmbed(self.floor).get_seat_list()
        await self.message.edit(embeds=embed, view=DatabaseMenuButtons(floor=self.floor))


class SeatSelectView(discord.ui.View):
    def __init__(self, message, floor: int):
        super().__init__(timeout=None)

        self.add_item(DatabaseMenuSeatSelect(message=message, floor=floor))
