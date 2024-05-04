import discord
from discord import app_commands, ui
from discord.ext import tasks, commands
import datetime
import time

backup_time = datetime.time(hour=10, minute=13, tzinfo=datetime.timezone.utc)

class Backups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_backups.start()

    @tasks.loop(time=backup_time)
    async def send_backups(self):
        guild = await self.bot.fetch_guild(913838786947977256)
        channel = await guild.fetch_channel(1224839093939343390)
        
        files = [discord.File('maps.json'), discord.File('players.json')]
        await channel.send(f'<t:{int(time.time())-1}:R>', files=files)

async def setup(bot):
    await bot.add_cog(Backups(bot))