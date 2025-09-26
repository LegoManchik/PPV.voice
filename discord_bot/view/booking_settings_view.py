import discord
from discord import ui
from discord.ext import commands

from discord_bot.data.database import TicketBookingDatabase


class BookingSettings(ui.LayoutView):
    def __init__(self, ctx: commands.Context):
        super().__init__()

        container = ui.Container()
        container.add_item(ui.Section(ui.TextDisplay("#  Настройки бронирования"), accessory=ui.Button(emoji="❓", style=discord.ButtonStyle.gray)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        container.add_item(ui.ActionRow(ui.Button(label=f"{'TEXT':⠀^10}"), ui.Button(label=f"{'TEXT':⠀^10}"), ui.Button(label=f"{'TEXT':⠀^10}")))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.Section(ui.TextDisplay("**Планировака зала**\nФайл для настройки"), accessory=ui.Button(label="Загрузить", emoji="📤", style=discord.ButtonStyle.gray)))
        container.add_item(ui.File(discord.File(fp="data/seats.json", filename="seats.json")))
        container.add_item(ui.Section(ui.TextDisplay("**Сбросить до стандартного вида**"), accessory=ui.Button(label="Сброс", emoji="🔁", style=discord.ButtonStyle.blurple)))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        self.add_item(container)


