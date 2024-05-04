import discord
from discord.ext import commands
from discord import app_commands
import json

class ProgressBot(commands.Bot):
    def __init__(self, config):
        intents = discord.Intents.all()
        super().__init__(command_prefix='=', intents=intents)
        self.config = config
        
    async def setup_hook(self) -> None:
        await self.load_extension('cogs.maps')
        await self.load_extension('cogs.players')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.rolelist')
        await self.load_extension('cogs.backups')
        synced = await bot.tree.sync()
        self.allowed_mentions = discord.AllowedMentions.none()
        print(f'Synced {len(synced)} command(s)')
    
if __name__ == '__main__':
    with open('config.json', 'r') as input:
        config = json.load(input)
    
    bot = ProgressBot(config)
    bot.run(bot.config['token'])