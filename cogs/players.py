import discord
from discord.ext import commands
from discord import app_commands
import json
import typing
import datetime
from util import response_embed

class Players(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = []
        self.load()
        
    group = app_commands.Group(name='player', description="Commands for managing players")
    
    @group.command(name='link', description='Link player\'s discord and their IGN')
    async def add_command(self, interaction: discord.Interaction, ign: str, country_code: str, member: discord.Member = None):
        player = self.get_player(ign=ign, member=member)
        if player:
            mention = "." if player['id'] == '-1' else f' and is linked to account <@{player["id"]}>.'
            res = f'A player with IGN ``{player["ign"]}`` already exists{mention}'
            await interaction.response.send_message(embed=response_embed(res, 'error'))
            return
        
        self.data.append({'id': str(member.id) if member else '-1', 'ign': ign, 'country_code': country_code.lower()})
        self.save()
        mention = f'<@{member.id}>' if member else 'Non-member'
        res = f'IGN: ``{ign}``\nDiscord member: {mention}\nCountry: :flag_{country_code}:'
        await interaction.response.send_message(embed=response_embed(res, 'success', 'Player linked'))
    
    @group.command(name='setprogress', description='Sets the player to the specified section on a given map.')
    async def setprogress_command(self, interaction: discord.Interaction, map: str, section: str, member: discord.Member = None, ign: str = None):
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return
        
        player = self.get_player(member=member, ign=ign)
        
        if player == None:
            await interaction.response.send_message(embed=response_embed('Could not find specified player.', 'error'))
            return
        
        ign = player['ign']
        
        await interaction.response.defer()
        response = await maps_cog.set_progress(ign, map, section, interaction)
        
        if response['error'] == -1:
            await interaction.followup.send(embed=response_embed(f'Map with the name ``{map}`` is not found.', 'error'))
            return
        
        if response['error'] == -2:
            await interaction.followup.send(embed=response_embed(f'Section with the name ``{section}`` is not found in the map ``{map}``.', 'error'))
            return
        
        if response['error'] == -3:
            await interaction.followup.send(embed=response_embed('Unknown error', 'error'))
            return
        
        message =  f'**Player:** {member.mention if member else "Non-member"} ``(IGN: {ign})``\n'
        message += f'**Map:** ``{map}``\n'
        message += f'**Section:** ``{response["old_progress"]} -> {response["new_progress"]}``\n\n'
        message += f'**Roles removed:** {", ".join([f"<@&{x.id}>" for x in response["removed_roles"]])}\n'
        message += f'**Roles given:** {", ".join([f"<@&{x.id}>" for x in response["given_roles"]])}'
        embed = response_embed(message, 'success', title='Progress updated', author=interaction.user)
        await interaction.followup.send(embed=embed)
        
    @group.command(name='setvictor', description='Set player as a victor of a specified map')
    async def setvictor_command(self, interaction: discord.Interaction, map: str, fails: int, date: str=None, member: discord.Member = None, ign: str = None):
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return
        
        player = self.get_player(member=member, ign=ign)
        if player == None:
            await interaction.response.send_message(embed=response_embed('Could not find specified player.', 'error'))
            return
        ign = player['ign']
            
        if date == None:
            date = datetime.datetime.now(datetime.timezone.utc).strftime('%b %d, %Y').lstrip("0").replace(" 0", " ")
        else:
            try:
                dt = datetime.datetime.strptime(date, '%b %d, %Y')
                date = dt.strftime('%b %d, %Y').lstrip("0").replace(" 0", " ")
            except ValueError:
                embed = response_embed('Date must follow the format ``Jan 1, 1999``.', 'error')
                await interaction.response.send_message(embed=embed)
                return
        
        await interaction.response.defer()
        response = await maps_cog.add_victor(ign, map, fails, date, interaction)
        
        if response['error'] == -1:
            await interaction.followup.send(embed=response_embed(f'Map with the name ``{map}`` is not found.', 'error'))
            return
        
        if response['error'] == -3:
            await interaction.followup.send(embed=response_embed('Unknown error', 'error'))
            return
        
        member_id = player['id']
        message =  f'**Player:** {f"<@{member_id}>" if member_id != "-1" else "Non-member"} ``(IGN: {ign})``\n'
        message += f'**Map:** ``{map}``\n'
        message += f'**Section:** ``{response["old_progress"]} -> {response["new_progress"]}``\n\n'
        message += f'**Roles removed:** {", ".join([f"<@&{x.id}>" for x in response["removed_roles"]])}\n'
        message += f'**Roles given:** {", ".join([f"<@&{x.id}>" for x in response["given_roles"]])}'
        embed = response_embed(message, 'success', title='Progress updated', author=interaction.user)
        await interaction.followup.send(embed=embed)
        
    
    @group.command(name='list', description='Show a list of all registered players')
    async def list_command(self, interaction: discord.Interaction):
        members_list = []
        non_members_list = []
        for id, player in self.data.items():
            if id == '-1':
                for ign, player in player.items():
                    non_members_list.append({'ign': ign, 'country_code': player['country_code']})
            else:
                members_list.append({'id': id, 'ign': player['ign'], 'country_code': player['country_code']})
    
        lines_members = []
        i = 1    
        for player in members_list:
            lines_members.append(f'{i}. <@{player["id"]}> - {player["ign"]} :flag_{player["country_code"]}:')
            i += 1
        #lines_members = lines_members[:(len(lines_members)-2)]
        
        lines_non_members = []
        for player in non_members_list:
            lines_non_members.append(f'{i}. ``Non-member`` - {player["ign"]} :flag_{player["country_code"]}:')
            i += 1
            
        #lines_non_members = lines_non_members[:(len(lines_non_members)-2)]
        
        lines = lines_members + lines_non_members
        
        players_per_page = 15
        
        embeds = []
        for i in range(0, len(lines), players_per_page):
            desc = '\n'.join(lines[i:min(i+players_per_page, len(lines))])
            embeds.append(discord.Embed(title='Linked players', color=discord.Color.yellow(), description=desc))
        
        for i in range(len(embeds)):
            embeds[i].set_footer(text=f'Page {i+1}/{len(embeds)}')
        
        await interaction.response.send_message(embed = embeds[0], view = PaginationView(embeds))
    
    @group.command(name='profile')
    async def profile_command(self, interaction: discord.Interaction, ign: str = None, member: discord.Member = None):
        player = self.get_player(ign=ign, member=member)
        
        if not player:
            embed = response_embed(f'Could not find player.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        mention = f'<@{player["id"]}>' if player["id"] != '-1' else 'Non-member'
        res = f'IGN: ``{player["ign"]}``\nDiscord member: {mention}\nCountry: :flag_{player["country_code"]}:'
        await interaction.response.send_message(embed=response_embed(res, 'success', 'Player profile'))
        
    
    @group.command(name='changediscord', description='Set the discord account to IGN')
    async def changediscord_command(self, interaction: discord.Interaction, new_member: discord.Member, ign: str = None, old_member: discord.Member = None):
        x = self.get_player(member=new_member)
        if x:
            embed = response_embed(f'Account <@{new_member.id}> is already linked to IGN ``{x["ign"]}``.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        player = self.get_player(ign=ign, member=old_member)
        if not player:
            embed = response_embed(f'Could not find player.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        old_id = '``Non-member``' if player['id'] == '-1' else f'<@{player["id"]}>'
        embed = response_embed(f'Changed discord account for player ``{ign}`` from {old_id} to <@{new_member.id}>', 'success')
        player['id'] = str(new_member.id)
        await interaction.response.send_message(embed=embed)
        self.save()
    
    @group.command(name='changename', description='Change name of a registered player')
    async def changename_command(self, interaction: discord.Interaction, new_name: str, old_name: str = None, member: discord.Member = None):
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return
        
        x = self.get_player(ign=new_name)
        if x:
            embed = response_embed(f'Account with the name ``{x["ign"]}`` already exists.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        player = self.get_player(ign=old_name, member=member)
        if not player:
            embed = response_embed(f'Could not find player.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        old_name = player['ign']
        embed = response_embed(f'Changed IGN for player ``{old_name}`` to ``{new_name}``.', 'success')
        player['ign'] = new_name
        await interaction.response.send_message(embed=embed)
        self.save()
        
        await interaction.channel.send('hi')
        
        maps_data = maps_cog.data
        for map_name, map in maps_data.items():
            to_update = False
            for section in map['sections']:
                if old_name in section['players']:
                    section['players'][section['players'].index(old_name)] = new_name
                    to_update = True
            for victor in map['victors']:
                if victor['name'] == old_name:
                    victor['name'] = new_name
                    to_update = True
            if to_update:
                await maps_cog.update_messages(map_name, interaction)
        
        maps_cog.save()
        
    @group.command(name='changecountry', description='Change country of a registered player')
    async def changecountry_command(self, interaction: discord.Interaction, new_country_code: str, ign: str = None, member: discord.Member = None):
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return
        
        player = self.get_player(ign=ign, member=member)
        if not player:
            embed = response_embed(f'Could not find player.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        embed = response_embed(f'Changed country for player ``{player["ign"]}`` to ``{new_country_code}``.', 'success')
        player['country_code'] = new_country_code
        await interaction.response.send_message(embed=embed)
        self.save()
        
        await interaction.response.defer()
        maps_data = maps_cog.data
        for map_name, map in maps_data.items():
            for victor in map['victors']:
                if victor['name'] == ign:
                    await maps_cog.update_messages(map_name, interaction)
                    break
        
        maps_cog.save()
    
    def get_player(self, ign: str = None, member: discord.Member = None):
        if not ign and not member:
            return None
        
        for player in self.data:
            if ign and player['ign'].lower() == ign.lower():
                return player
            
            if member and player['id'] == str(member.id):
                return player
        
        return None
        
    def load(self):
        f = open('players.json', 'r')
        json_obj = f.read()
        self.data = json.loads(json_obj)
        
    def save(self):
        json_obj = json.dumps(self.data, indent=4)
        f = open('players.json', 'w')
        f.write(json_obj)    
    
    @setprogress_command.autocomplete('map')
    @setvictor_command.autocomplete('map')
    async def map_autocompletion(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return []
        maps_data = maps_cog.data
        
        map_choices = []
        for map in maps_data:
            if current.lower() in map.lower():
                map_choices.append(app_commands.Choice(name=map, value=map))
                
        return map_choices[:25]
        
    @setprogress_command.autocomplete('section')
    async def edit_autocompletion(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        maps_cog = self.bot.get_cog('Maps')
        if not maps_cog:
            return []
        maps_data = maps_cog.data
                
        args = interaction.namespace
        
        if 'map' in args:
            if maps_data.get(args['map']):
                choices = [app_commands.Choice(name=x['name'], value=x['name']) for x in maps_data[args['map']]['sections']]
        
        real_choices = []
        for choice in choices:
            if current.lower() in choice.name.lower():
                real_choices.append(choice)
        
        return real_choices[:25]  
    
    @setvictor_command.autocomplete('ign')
    @setprogress_command.autocomplete('ign')
    @changename_command.autocomplete('old_name')
    @changecountry_command.autocomplete('ign')
    @changediscord_command.autocomplete('ign')
    @profile_command.autocomplete('ign')
    async def ign_autocomplation(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        choices = []
        for player in self.data:
            if current.lower() in player['ign'].lower():
                choices.append(app_commands.Choice(name=player['ign'], value=player['ign']))
        return choices[:25]

class PaginationView(discord.ui.View):
    def __init__(self, pages):
        super().__init__()
        self.page = 0
        self.pages = pages
        
        if len(self.pages) > 1:
            prev = discord.ui.Button(label="<", style=discord.ButtonStyle.green, custom_id="prev")
            prev.disabled = True
            prev.callback = self.prev_button
            
            next = discord.ui.Button(label=">", style=discord.ButtonStyle.green, custom_id="next")
            next.callback = self.next_button
            
            self.add_item(prev)
            self.add_item(next)

    async def prev_button(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1

        if self.page == 0:
            for child in self.children:
                if child.custom_id == 'prev':
                    child.disabled = True
        
        for child in self.children:
            if child.custom_id == 'next':
                child.disabled = False
        
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)

    async def next_button(self, interaction: discord.Interaction):
        if self.page < len(self.pages) - 1:
            self.page += 1
        
        if self.page == len(self.pages)-1:
            for child in self.children:
                if child.custom_id == 'next':
                    child.disabled = True
        
        for child in self.children:
            if child.custom_id == 'prev':
                child.disabled = False
        
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)
        
async def setup(bot):
    await bot.add_cog(Players(bot))