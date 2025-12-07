import os

from typing import Optional

import discord
from discord.ui import Select, View
from discord import TextStyle

import config
from utils.sort_utils import first_number


class FolderSelect(Select):
    def __init__(self, message):
        options = []

        for folder in sorted(os.listdir('./audio_files'), key=first_number):
            if '.' not in folder:
                options.append(discord.SelectOption(
                    label=folder,
                    value=f'./audio_files/{folder}',
                    description=f"",
                    emoji='📁'
                ))
        else:
            if not (len(options) > 0):
                options.append(discord.SelectOption(
                    label=f"Папок с аудио файлами не найдено!",
                    description=f"", value="none_folders", emoji='📁'
                ))

        self.message = message

        super().__init__(
            custom_id='folder_select',
            placeholder="Выберите папку",
            options=options
        )

    async def callback(self, inter: discord.MessageInteraction):
        if self.values[0] != "none_folders":
            files_list = ''

            for file in sorted(os.listdir(self.values[0]), key=first_number):
                files_list += f'```{file}```'
            else:
                if files_list == '':
                    files_list += '```Здесь пусто!```'

            embed = discord.Embed(title=self.values[0], description=files_list, color=config.COLOR)
            await inter.response.edit_message(embed=embed,
                                              view=FolderButtons(folder=self.values[0], message=self.message))
        else:
            await inter.response.defer()


class FileSelect(Select):
    def __init__(self, folder: str, message):
        options = []
        emojis = {'webm': '🎵', 'm4a': '🎵', 'mp3': '🎵'}

        path = sorted(
            os.listdir(f'./{folder}'),
            key=first_number
        )

        if len(path) > 0:
            for file in path:
                options.append(discord.SelectOption(
                    label=file,
                    description=f"",
                    value=f'{folder}/{file}',
                    emoji=emojis[file.split('.')[-1]]
                ))
        else:
            options.append(discord.SelectOption(
                label=f"Аудио файлов не найдено!",
                description=f"", value="none_files", emoji='❌'
            ))

        self.folder = folder
        self.message = message

        super().__init__(
            custom_id='file_select',
            placeholder="Выберите файл",
            options=options
        )

    async def callback(self, inter: discord.MessageInteraction):
        if self.values[0] != "none_files":
            await inter.response.send_message(
                embed=discord.Embed(title=self.values[0], description='Выберите действие...', color=config.COLOR),
                view=FileButtons(self.values[0], self.message), ephemeral=True, delete_after=10)
        else:
            await inter.response.defer()


class SetNameFolderModal(discord.ui.Modal):
    name = discord.ui.TextInput(
        label="Название",
        placeholder="",
        custom_id=f"set_folder_name",
        style=TextStyle.short,
        max_length=66
    )

    def __init__(self, *, title="Переименовать файл", timeout=None, custom_id="rename_file", message):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        os.mkdir(f'./audio_files/{self.name.value}')

        text = ''
        for folder in os.listdir('./audio_files'):
            if '.' not in folder:
                text += f'```{folder}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='./audio_files', description=text, color=config.COLOR),
                                view=MkDirButtons(message=self.message))

        await interaction.response.send_message(
            embed=discord.Embed(description=f'```Папку {self.name.value} создана```', color=config.COLOR),
            ephemeral=True, delete_after=3)


class RenameFolderModal(discord.ui.Modal):
    name = discord.ui.TextInput(
        label="Название",
        placeholder="",
        custom_id=f"folder_name",
        style=TextStyle.short,
        max_length=66
    )

    def __init__(self, *, title="Переименовать папку", timeout=None, custom_id="rename_folder", folder: str, message):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

        self.folder = folder
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):

        path = self.folder.split('/')

        path[-1] = self.name.value

        os.rename(self.folder, '/'.join(path))

        text = ''
        for file in os.listdir('/'.join(path)):
            if '.' not in file:
                text += f'```{file}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR),
                                view=FolderButtons('/'.join(path), message=self.message))

        await interaction.response.send_message(
            embed=discord.Embed(description=f'```{self.folder} -> {"/".join(path)}```', color=config.COLOR),
            ephemeral=True, delete_after=3)


class RenameFileModal(discord.ui.Modal):
    name = discord.ui.TextInput(
        label="Название",
        placeholder="",
        custom_id=f"file_name",
        style=TextStyle.short,
        max_length=66
    )

    def __init__(self, *, title="Переименовать файл", timeout=None, custom_id="rename_file", file: str, message):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

        self.file = file
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):

        path = self.file.split('/')

        path[-1] = self.name.value + '.' + path[-1].split('.')[-1]

        os.rename(self.file, '/'.join(path))

        path.pop(-1)
        text = ''

        for file in os.listdir('/'.join(path)):
            text += f'```{file}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR),
                                view=FolderButtons('/'.join(path), message=self.message))

        await interaction.response.send_message(embed=discord.Embed(
            description=f'```{self.file} -> {"/".join(path)}/{self.name.value}.{self.file.split(".")[-1]}```',
            color=config.COLOR), ephemeral=True, delete_after=3)


class MkDirButtons(View):
    def  __init__(self, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.message = message

        self.add_item(FolderSelect(message=message))

    @discord.ui.button(label="Создать папку", style=discord.ButtonStyle.gray, emoji="➕")
    async def mkdir_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetNameFolderModal(message=self.message))


class FolderButtons(View):
    def __init__(self, folder: str, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.folder = folder
        self.message = message

        if folder != './audio_files':
            self.add_item(FileSelect(folder, message))

    @discord.ui.button(label="Переименовать", style=discord.ButtonStyle.gray, emoji="✍", row=1)
    async def rename_dir_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameFolderModal(folder=self.folder, message=self.message))

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red, emoji="🗑", row=1)
    async def delete_dir_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        path = self.folder.split('/')
        path.pop(-1)
        text = ''

        for file in os.listdir(self.folder):
            os.remove(f'{self.folder}/{file}')
        else:
            os.removedirs(self.folder)

        for folder in os.listdir('/'.join(path)):
            if '.' not in folder:
                text += f'```{folder}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR),
                                view=MkDirButtons(message=self.message))

        await interaction.response.send_message(embed=discord.Embed(
            description=f'```{self.folder} удалён```', color=0xE74C3C), ephemeral=True, delete_after=3)

        await interaction.delete_original_response()

    @discord.ui.button(label="Вернуться", style=discord.ButtonStyle.gray, emoji="⬅", row=2)
    async def back_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.edit(embed=get_filelist_embed(os.listdir('./audio_files')), view=MkDirButtons(self.message))


class FileButtons(View):
    def __init__(self, file: str, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.file = file
        self.message = message

    @discord.ui.button(label="Переименовать", style=discord.ButtonStyle.gray, emoji="✍", row=1)
    async def rename_file_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameFileModal(file=self.file, message=self.message))

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red, emoji="🗑", row=1)
    async def delete_file_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        path = self.file.split('/')
        path.pop(-1)
        text = ''

        os.remove(self.file)

        for file in os.listdir('/'.join(path)):
            text += f'```{file}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR),
                                view=FolderButtons('/'.join(path), message=self.message))

        await interaction.response.send_message(embed=discord.Embed(
            description=f'```{self.file} удалён```', color=0xE74C3C), ephemeral=True, delete_after=3)

        await interaction.delete_original_response()

    @discord.ui.button(label="Вернуться", style=discord.ButtonStyle.gray, emoji="⬅", row=2)
    async def back_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.edit(embed=get_filelist_embed(os.listdir('./audio_files')), view=MkDirButtons(self.message))


def get_filelist_embed(filelist: list) -> discord.Embed:
    list_ = ''
    for file in sorted(filelist, key=first_number):
        if '.' not in file:
            list_ += f'```{file}```'
    else:
        if list_ == '':
            list_ += '```Здесь пусто!```'

    return discord.Embed(title='./audio_files', description=list_, color=config.COLOR)
