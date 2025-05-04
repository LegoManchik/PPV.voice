import json

import discord
from discord.ext import commands

LANGUAGE_FILES = {"ru": "ru_ru.json", "en": "en_us.json"}


class LangContext(commands.Context):
    def __init__(self, message, bot, view, **kwargs):
        super().__init__(message=message, bot=bot, view=view, **kwargs)
        self.lang = 'en'

    def set_lang(self, lang: str):
        self.lang = lang


class Localization:
    def __init__(self):
        pass

    @classmethod
    def translatable(cls, key: str, lang: str):
        with open(f'lang/{LANGUAGE_FILES.get(lang)}', 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data.get(key)

    @classmethod
    def translatable_embed(cls, embed: discord.Embed, key: str, lang):
        with open(f'lang/{LANGUAGE_FILES.get(lang)}', 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file).get(key)

        embed.title = data.get('title')
        embed.description = data.get('description')

        if data.get('image') is not None:
            embed.set_image(url=data.get('image'))

        return embed
