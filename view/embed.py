import discord

import config

from data.data_classes.archive import Archive


class BaseEmbeds:

    @staticmethod
    def error(message: str) -> discord.Embed:
        return discord.Embed(description=message, color=discord.Color.red())

    @staticmethod
    def info(message: str) -> discord.Embed:
        return discord.Embed(description=message, color=config.COLOR)

    @staticmethod
    def success(message: str) -> discord.Embed:
        return discord.Embed(description=message, color=discord.Color.green())

    @staticmethod
    def player(message: str = "Сейчас ничего не играет :("):
        embed = discord.Embed(
            title='Сейчас играет 🎶:',
            color=config.COLOR,
            description=f'```{message}```'
        )
        embed.set_footer(text="")
        return embed

    @staticmethod
    def archive() -> discord.Embed:
        embed = discord.Embed(
            title="Архив:",
            color=config.COLOR
        )
        return embed

    @staticmethod
    def processed_archive(embed: discord.Embed, archive: Archive, last_track: str = None) -> discord.Embed:
        embed.clear_fields()

        if last_track is not None:
            archive.add_track(last_track)

        track_list = archive.track_list
        if len(track_list) > 6:
            embed.add_field(name=f"И ещё ({len(track_list) - 6}) треков...", value="", inline=False)

        for track in track_list[-6:][:-1]:
            embed.add_field(name="", value=f"`{track}`", inline=False)

        embed.add_field(name="Последний трек:", value=f"`{archive.last_track}`", inline=False)

        return embed