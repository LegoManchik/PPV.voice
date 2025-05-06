import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime

import config


class BackupSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DB_PATH = 'data/tickets.db'
        self.BACKUPS_DIR = 'backups'
        self.BACKUP_INTERVAL = 6
        self.MAX_BACKUPS = 10
        self.auto_backup.start()

    def cog_unload(self):
        self.auto_backup.cancel()

    @tasks.loop(hours=6)
    async def auto_backup(self):
        """Автоматическое создание резервных копий"""
        await self.create_backup(f"auto_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db")

    @auto_backup.before_loop
    async def before_auto_backup(self):
        await self.bot.wait_until_ready()
        if not os.path.exists(self.BACKUPS_DIR):
            os.makedirs(self.BACKUPS_DIR)

    async def create_backup(self, backup_name):
        try:
            backup_path = os.path.join(self.BACKUPS_DIR, backup_name)

            source = sqlite3.connect(self.DB_PATH)
            backup = sqlite3.connect(backup_path)
            with backup:
                source.backup(backup)
            source.close()
            backup.close()

            backups = sorted(os.listdir(self.BACKUPS_DIR))
            if len(backups) > self.MAX_BACKUPS:
                for old_backup in backups[:-self.MAX_BACKUPS]:
                    os.remove(os.path.join(self.BACKUPS_DIR, old_backup))

            return backup_name
        except Exception as e:
            print(f'Ошибка при создании бэкапа: {e}')
            return None

    @commands.hybrid_command(name="backup")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def backup(self, ctx):
        """Создать бэкап вручную"""
        backup_name = await self.create_backup(f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db")
        if backup_name:
            await ctx.send(embed=discord.Embed(description=f'✅ Резервная копия создана: `{backup_name}`'))
        else:
            await ctx.send(embed=discord.Embed(description='❌ Не удалось создать резервную копию'))

    @commands.hybrid_command(name="backups_info")
    @commands.has_any_role(config.SUPERVISOR_ROLE_ID, config.OPERATOR_ROLE_ID)
    async def backups_info(self, ctx):
        """Показать информацию о бэкапах"""
        backups = sorted(os.listdir(self.BACKUPS_DIR), reverse=True)
        if not backups:
            await ctx.send("Нет доступных резервных копий")
            return

        embed = discord.Embed(title="📊 Информация о резервных копиях", color=0x00ff00)

        recent_backups = "\n".join(backups[:5])
        embed.add_field(name="Последние бэкапы", value=recent_backups, inline=False)

        total_size = sum(os.path.getsize(os.path.join(self.BACKUPS_DIR, f)) for f in backups)
        embed.add_field(name="Всего бэкапов", value=str(len(backups)))
        embed.add_field(name="Общий размер", value=f"{total_size / 1024:.2f} KB")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BackupSystem(bot))
