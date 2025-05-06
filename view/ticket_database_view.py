import asyncio

import discord
from discord import TextStyle

import config
from data.database import TicketBookingDatabase, SeatStatus
from utils.localization import Localization


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

            status = "✅"
            avalible = self.db.is_avalible(self.floor, seat[0])
            if not avalible:
                if seat[1] is None:
                    status = "🟨"
                else:
                    status = "🟥"

            embed.add_field(name="", value=f"```{status} {seat[0]}```", inline=True)
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

        back_button = discord.ui.Button(emoji="⬅", style=discord.ButtonStyle.gray, custom_id="database_menu_back", disabled=floor==1, row=1)
        next_button = discord.ui.Button(emoji="➡", style=discord.ButtonStyle.gray, custom_id="database_menu_next", disabled=floor==3, row=1)

        cancel_reservetion_button = discord.ui.Button(label="Отменить бронь", emoji="🚩", style=discord.ButtonStyle.gray, custom_id="database_menu_cancel_reservetion", row=2)
        add_reservetion_button = discord.ui.Button(label="Добавить бронь", emoji="🚩", style=discord.ButtonStyle.gray, custom_id="database_menu_add_reservetion", row=2)

        back_button.callback = self.back_callback
        next_button.callback = self.next_callback
        cancel_reservetion_button.callback = self.cancel_reservetion_callback
        add_reservetion_button.callback = self.add_reservetion_callback

        self.add_item(back_button)
        self.add_item(next_button)
        self.add_item(cancel_reservetion_button)
        self.add_item(add_reservetion_button)

    async def back_callback(self, interaction: discord.Interaction):
        embeds = DatabaseMenuEmbed(self.floor - 1).get_seat_list()
        await interaction.response.edit_message(embeds=embeds, view=DatabaseMenuButtons(self.floor-1))

    async def next_callback(self, interaction: discord.Interaction):
        embeds = DatabaseMenuEmbed(self.floor + 1).get_seat_list()
        await interaction.response.edit_message(embeds=embeds, view=DatabaseMenuButtons(self.floor+1))

    async def cancel_reservetion_callback(self, interactrion: discord.Interaction):
        await interactrion.response.send_message(view=SeatSelectView(interactrion.message, floor=self.floor), ephemeral=True)

    async def add_reservetion_callback(self, interactrion: discord.Interaction):
        await interactrion.response.send_message(view=SeatSelectView(interactrion.message, floor=self.floor, add_seat=True), ephemeral=True)


class DatabaseMenuSeatSelect(discord.ui.Select):
    def __init__(self, message, floor: int, add_seat: bool = False):
        options = []

        self.db = TicketBookingDatabase()

        self.floor = floor
        self.message = message
        self.add_seat = add_seat

        for seat in self.db.get_seat_list(floor):
            emoji = ""
            if seat[1] is None:
                emoji = "⚫"
            else:
                emoji = "🔵"

            options.append(
                discord.SelectOption(
                    label=seat[0],
                    value=f'{seat[0]}_{seat[1]}',
                    description=f"{seat[1]} | {seat[2]}",
                    emoji=emoji
                )
            )

        placeholder = {False: "Удалить бронь...", True: "Добавить бронь..."}

        super().__init__(
            custom_id='seat_select',
            placeholder=placeholder.get(add_seat),
            options=options
        )

    async def callback(self, inter: discord.Interaction):
        if self.values[0].split("_")[1] != "None":
            seat = self.values[0].split("_")[0]
            self.db.remove_user(self.floor, seat)
            self.db.set_seat_status(self.floor, seat, SeatStatus.AVAILABLE)

            embed = DatabaseMenuEmbed(self.floor).get_seat_list()
            await self.message.edit(embeds=embed, view=DatabaseMenuButtons(floor=self.floor))
            await inter.response.edit_message(view=SeatSelectView(self.message, self.floor))
        elif self.add_seat:
            await inter.response.edit_message(view=UserSelectView(self.message, self.floor, self.values[0].split("_")[0]))


class SeatSelectView(discord.ui.View):
    def __init__(self, message, floor: int, add_seat: bool = False):
        super().__init__(timeout=None)

        self.add_item(DatabaseMenuSeatSelect(message=message, floor=floor, add_seat=add_seat))


class UserSelect(discord.ui.UserSelect):
    def __init__(self, message, floor: int, seat: str):
        self.message = message
        self.floor = floor
        self.seat = seat

        super().__init__(
            custom_id='user_select',
            placeholder="Выберите пользователя...",
        )

    async def callback(self, inter: discord.Interaction):
        await inter.response.send_modal(AddPlayersToDatabaseModal(message=self.message, floor=self.floor, seat=self.seat, user=self.values[0]))
        await inter.delete_original_response()


class UserSelectView(discord.ui.View):
    def __init__(self, message, floor: int, seat: str):
        super().__init__(timeout=None)

        self.add_item(UserSelect(message=message, floor=floor, seat=seat))


class AddPlayersToDatabaseModal(discord.ui.Modal):
    players = discord.ui.TextInput(
        label="modal_label.player_list",
        placeholder="modal_placeholder.prompt",
        custom_id=f"players_list",
        style=TextStyle.short,
        max_length=100
    )

    def __init__(self, *, title: str = "modal_title.player_list", timeout=None, custom_id: str = "add_players_database", floor: int, seat: str, user: discord.User, message):
        super().__init__(title=Localization.translatable(title, "ru"), timeout=timeout, custom_id=custom_id)

        self.players.label = Localization.translatable(self.players.label, "ru")
        self.players.placeholder = Localization.translatable(self.players.placeholder, "ru")

        self.message = message
        self.floor = floor
        self.seat = seat
        self.user = user

        self.db = TicketBookingDatabase()

    async def on_submit(self, interaction: discord.Interaction):
        self.db.add_user(int(self.floor), self.seat, self.user.id, self.players.value)
        self.db.set_seat_status(self.floor, self.seat, SeatStatus.UNAVAILABLE)
        await self.message.edit(embeds=DatabaseMenuEmbed(floor=self.floor).get_seat_list())
        await interaction.response.defer()
