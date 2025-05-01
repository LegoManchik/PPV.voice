import os

from typing import Optional

import discord
from discord.ui import Select, View
from discord import TextStyle

import config


class FolderSelect(Select):
    def __init__(self, message):
        options = []

        path = os.listdir('./audio_files')

        for folder in path:
            if not(folder.endswith('.webm')):
                options.append(discord.SelectOption(
                    label=folder,
                    value=f'./audio_files/{folder}',
                    description=f"",
                    emoji='📁'
                ))
        else:
            if not(len(options) > 0):
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

            for file in os.listdir(self.values[0]):
                files_list += f'```{file}```'
            else:
                if files_list == '':
                    files_list += '```Здесь пусто!```'


            embed = discord.Embed(title=self.values[0], description=files_list, color=config.COLOR)
            await inter.response.edit_message(embed=embed, view=FolderButtons(folder=self.values[0], message=self.message))        


class FileSelect(Select):
    def __init__(self, folder: str, message):
        options = []
        emojis = {'webm': '🎵', 'm4a': '🎵'}
        
        path = os.listdir(f'./{folder}')
        
        if len(path) > 0:
            for file in path:
                if file.endswith('.webm'):
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
            await inter.response.send_message(embed=discord.Embed(title=self.values[0], description='Выберите действие...', color=config.COLOR),
                view=FileButtons(self.values[0], self.message), ephemeral=True, delete_after=10)


class SetNameFolderModal(discord.ui.Modal):
   
    name = discord.ui.TextInput(
            label="Название",
            placeholder="",
            custom_id=f"set_folder_name",
            style=TextStyle.short,
            max_length=66
            )

    def __init__(self, *, title="Переименовать файл", timeout = None, custom_id="rename_file", message):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

        self.message = message
        
    async def on_submit(self, interaction: discord.Interaction):
        os.mkdir(f'./audio_files/{self.name.value}')

        text = ''
        for folder in os.listdir('./audio_files'):
            if not(folder.endswith('.webm')):
                text += f'```{folder}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'
        
        await self.message.edit(embed=discord.Embed(title='./audio_files', description=text, color=config.COLOR), 
            view=MkDirButtons(message=self.message))

        await interaction.response.send_message(embed=discord.Embed(description=f'```Папку {self.name.value} создана```', color=config.COLOR), 
            ephemeral=True, delete_after=3)


class RenameFolderModal(discord.ui.Modal):
   
    name = discord.ui.TextInput(
            label="Название",
            placeholder="",
            custom_id=f"folder_name",
            style=TextStyle.short,
            max_length=66
            )

    def __init__(self, *, title="Переименовать папку", timeout = None, custom_id="rename_folder", folder: str, message):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

        self.folder = folder
        self.message = message
        
    async def on_submit(self, interaction: discord.Interaction):
        
        path = self.folder.split('/')
        
        path[-1] = self.name.value

        os.rename(self.folder, '/'.join(path))

        text = ''
        for file in os.listdir('/'.join(path)):
            text += f'```{file}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'
        
        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR), 
            view=FolderButtons('/'.join(path), message=self.message))

        await interaction.response.send_message(embed=discord.Embed(description=f'```{self.folder} -> {"/".join(path)}```', color=config.COLOR),
            ephemeral=True, delete_after=3)


class RenameFileModal(discord.ui.Modal):
   
    name = discord.ui.TextInput(
            label="Название",
            placeholder="",
            custom_id=f"file_name",
            style=TextStyle.short,
            max_length=66
            )

    def __init__(self, *, title="Переименовать файл", timeout = None, custom_id="rename_file", file: str, message):
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
    def __init__(self, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.message = message

        self.add_item(FolderSelect(message=message))
    
    @discord.ui.button(label="Создать папку", style=discord.ButtonStyle.gray, emoji="➕")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetNameFolderModal(message=self.message))
    

class FolderButtons(View):
    def __init__(self, folder: str, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.folder = folder
        self.message = message

        if folder != './audio_files':
            self.add_item(FileSelect(folder, message))
    
    @discord.ui.button(label="Переименовать", style=discord.ButtonStyle.gray, emoji="✍")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameFolderModal(folder=self.folder, message=self.message))

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red, emoji="🗑")
    async def button1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        path = self.folder.split('/')
        path.pop(-1)
        text = ''

        for file in os.listdir(self.folder):
            os.remove(f'{self.folder}/{file}')
        else:
            os.removedirs(self.folder)

        for folder in os.listdir('/'.join(path)):
            if not(folder.endswith(".webm")):
                text += f'```{folder}```'
        else:
            if text == '':
                text += '```Здесь пусто!```'

        await self.message.edit(embed=discord.Embed(title='/'.join(path), description=text, color=config.COLOR), 
            view=MkDirButtons(message=self.message))

        await interaction.response.send_message(embed=discord.Embed(
            description=f'```{self.folder} удалён```', color=0xE74C3C), ephemeral=True, delete_after=3)
        
        await interaction.delete_original_response()
    

class FileButtons(View):
    def __init__(self, file: str, message):
        super().__init__(timeout=None)

        self.value: Optional[bool] = None

        self.file = file
        self.message = message
    
    @discord.ui.button(label="Переименовать", style=discord.ButtonStyle.gray, emoji="✍")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameFileModal(file=self.file, message=self.message))

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red, emoji="🗑")
    async def button1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
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

       

