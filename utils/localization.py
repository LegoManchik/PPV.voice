import json

import discord
import enum
from discord.ext import commands

import config


class Language(enum.Enum):
    RU = "ru"
    EN = "en"

    @classmethod
    def lang_file_path(cls, lang) -> str:
        match lang:
            case Language.RU.value:
                return "ru_ru.json"
            case Language.EN.value:
                return "en_us.json"
        return "ru_ru.json"

    @classmethod
    def lang_role_get(cls, lang) -> int:
        match lang:
            case Language.RU.value:
                return config.RU_ROLE_ID
            case Language.EN.value:
                return config.EN_ROLE_ID
        return 0


class LangContext(commands.Context):
    def __init__(self, message, bot, view, **kwargs):
        super().__init__(message=message, bot=bot, view=view, **kwargs)

    @classmethod
    async def get_context_from_interaction(cls, bot: commands.Bot, interaction: discord.Interaction) -> commands.Context:
        ctx = await bot.get_context(interaction.message) if interaction.message else await bot.get_context(
            interaction)
        ctx.author = interaction.user
        ctx.channel = interaction.channel
        ctx.interaction = interaction
        return ctx


class Localization:

    @classmethod
    def translatable(cls, key: str, lang: str) -> str | dict:
        with open(f'lang/{Language.lang_file_path(lang)}', 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data.get(key)

    @classmethod
    def translatable_embed(cls, embed: discord.Embed, key: str, lang: str) -> discord.Embed:
        with open(f'lang/{Language.lang_file_path(lang)}', 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file).get(key)

        embed.title = data.get('title')
        embed.description = data.get('description')

        if data.get('image') is not None:
            embed.set_image(url=data.get('image'))

        if data.get("author") is not None:
            embed.set_author(name=data.get("author").get("name"), icon_url=data.get("author").get("icon"))

        if data.get("fields") is not None:
            for field in data.get("fields"):
                embed.add_field(name=field["name"], value=field["value"], inline=field['inline'])

        return embed
