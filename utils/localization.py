import json

import discord


class Localization:
    def __init__(self):
        pass

    @classmethod
    def translatable(cls, key: str, lang: str):
        with open('lang/{0}'.format({"ru": "ru_ru.json", "en": "en_us.json"}.get(lang)), 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data.get(key)

    @classmethod
    def translatable_embed(cls, embed: discord.Embed, key: str, lang):
        with open('lang/{0}'.format({"ru": "ru_ru.json", "en": "en_us.json"}.get(lang)), 'r+', encoding="utf-8") as json_file:
            data = json.load(json_file).get(key)

        embed.title = data.get('title')
        embed.description = data.get('description')

        return embed
