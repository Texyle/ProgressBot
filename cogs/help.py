import discord
from discord import app_commands, ui
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embeds = self.create_embeds()
        
    @app_commands.command(name='help', description='Help')
    async def help_command(self, interaction: discord.Interaction):
        embed = self.embeds['1']
        
        select = ui.Select(options=[
            discord.SelectOption(label='Adding a new map', value='1'),
            discord.SelectOption(label='Map properties', value='2'),
            discord.SelectOption(label='Configuring roles', value='3'),
            discord.SelectOption(label='Updating player progress', value='4')
        ])
        view = ui.View()
        view.add_item(select)
        
        async def select_callback(interaction):
            await interaction.message.edit(embed = self.embeds[select.values[0]])
            await interaction.response.defer()
        
        select.callback = select_callback
                
        await interaction.response.send_message(embed=embed, view=view)
        
    def create_embeds(self):
        embeds = {}
        
        e1 = discord.Embed(title='Adding a new map')
        desc = '1. ``/map add [map name] [sections]`` to create a new map. For extra maps put "-" in the sections field (meaning no sections). Sections should be separated by semi colons (;). You may also add players in any section after a colon, separated by commas (,), but make sure to use their current IGN otherwise they won\'t be automatically updated later (or just don\'t do that if you\'re not sure, see "Updating player progress"). Blank spaces are ignored. '
        desc += 'Use ``/map printsections`` on any existing map to see examples of valid sections format. Both name and sections may easily be edited in the next step.'
        desc += '\n\n2. Use ``/map edit [map name] [field] [value]`` to edit any of the optional fields. See "Map properties" for more info.'
        desc += '\n\n3. Use ``/map send [map name] [channel]`` to send a formatted message to the desired channel. This message will automatically update on any changes made to the map (if you use this command again to send a new message the old one will no longer update). The bot will automatically deal with character limits by sending multiple messages or deleting empty ones.'
        e1.description = desc
        embeds['1'] = e1
        
        e2 = discord.Embed(title='Map properties')
        desc = 'Map properties define how a map message will look like. They can be configured using ``/map edit``.\n'
        desc += '* **Name:** The name that will be used in commands and displayed in the title of the map message.\n'
        desc += '* **Sections:** Sets the names of the sections, as well as player names that are on those sections. For small changes it is recommended to use ``/map printsections`` and copy and edit the message that it gives (it is already formatted properly).\n'
        desc += '* **Progress start:** The section starting from which player names will be listed.\n'
        desc += '* **Emoji:** Emoji that will be displayed next to every section that has players in it as well as around the victor role.\n'
        desc += '* **Release date:** Release date that shows above the victor list. Its just a string so it will be displayed however you input it, so please make sure to format it properly.\n'
        desc += '* **Fails message:** The word that will be put in place of "sky" in "sky fails". (e.g. "level 20" for Abyss)\n'
        desc += '* **No victors message:** Message that displays after the "0 Victors - " when a map has no victors. Intended for information about server PB, empty by default.'
        e2.description = desc
        embeds['2'] = e2
        
        e3 = discord.Embed(title='Configuring roles')
        desc = 'Each section has an optional role parameter, which is set to none by default. It can be changed using ``/map setrole`` and ``/map removerole``. If a section has an assigned role, it will be separated by lines in the formatted message.'
        e3.description = desc
        embeds['3'] = e3
        
        e4 = discord.Embed(title='Updating player progress')
        desc = 'Every player must be registered once using ``/player link [member] [ign] [country code]``. This is done for convenience of not having to remember each players ign and just selecting them from the members list. Country code is the 2 letters that come after the "flag_" in the emoji.'
        desc += '\n\nUpdating players progress is done using 2 commands: ``/player setprogress [member] [map name] [section]`` and ``/player setvictor [member] [map name] [fails] [date(optional)]``. When selecting sections use the suggested values from autocompletion. Not specifying the date automatically sets it to current date.'
        desc += '\n\nFor players that aren\'t members of the server there is a work-around link command ``/player link-nonmember [ign] [country code]``. To update their progress you can use the same 2 commands but with the hidden ``nonmember_ign`` argument. The member argument can be set to whatever, it is ignored.'
        e4.description = desc
        embeds['4'] = e4
        
        return embeds
        
    @app_commands.command(name='reloadcogs', description='reload cogs')
    async def reloadcogs_command(self, interaction: discord.Interaction):
        await self.bot.reload_extension('cogs.maps')
        await self.bot.reload_extension('cogs.players')
        await self.bot.reload_extension('cogs.help')
        await self.bot.reload_extension('cogs.rolelist')
        await interaction.response.send_message("reloaded cogs")
    
async def setup(bot):
    await bot.add_cog(Help(bot))