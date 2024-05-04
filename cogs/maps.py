import discord
from discord import app_commands
from discord.ext import commands
import json
import typing
from util import response_embed, align_string
import datetime
import datefinder
from emoji import emoji_count
import re

class Maps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        self.cached_messages = {}
        self.load()
        
    group = app_commands.Group(name='map', description="Add new maps and edit existing ones")
    
    @group.command(name='add', description='Add new map')
    async def add_command(self, interaction: discord.Interaction, name: str, sections: str):
        if self.data.get(name):
            embed=response_embed('Map already exists! Use ``/map edit`` to edit.', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        sections_arr = []
        if sections != '-':
            section_strings = [x.strip() for x in sections.split(';')]
            for section in section_strings:
                players = []
                colon_ind = section.find(':')
                if colon_ind != -1:
                    players = [x.strip for x in section[(colon_ind+1):].split(',')]
                    section = section[:colon_ind]
                sections_arr.append({'name': section, 'players': players, 'role': -1})
        
        self.data[name] = {'sections': sections_arr, 
                           'victors': [], 
                           'victor_role': -1, 
                           'progress_start': 0, 
                           'emoji': '⚪', 
                           'messages': [], 
                           'release_date': 'UNKNOWN DATE',
                           'starting_section_message': '-',
                           'fails_message': 'sky',
                           'no_victors_message': '-',
                           'victor_separators': [],
                           'hide_roles': False}
        self.save()
        message = f'Map ``{name}`` successfully added. Use ``/map send`` to send formatted map message or ``/map edit`` to edit its properties.'
        embed = response_embed(message, 'success', title='Map added')
        await interaction.response.send_message(embed=embed)
    
    @app_commands.choices(field=[
                           discord.app_commands.Choice(name='Name', value='name'),
                           discord.app_commands.Choice(name='Sections', value='sections'),
                           discord.app_commands.Choice(name='Progress start', value='progress start'),
                           discord.app_commands.Choice(name='Emoji', value='emoji'),
                           discord.app_commands.Choice(name='Starting section message', value='starting section message'),
                           discord.app_commands.Choice(name='Fails message', value='fails message'),
                           discord.app_commands.Choice(name='No victors message', value='no victors message'),
                           discord.app_commands.Choice(name='Victor separators', value='victor separators'),
                           discord.app_commands.Choice(name='Hide role separators', value='hide roles')])
    @group.command(name='edit', description='Edit properties of a map')
    async def edit_command(self, interaction: discord.Interaction, map_name: str, field: str, value: str):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        if map_name == 'Magnum Opus':
            embed = response_embed(f'DO NOT EDIT MAGNUP OPUS!!! (ask <@269105396587823104>)\n', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        if field == 'name':
            if self.data.get(value):
                embed = response_embed(f'A map with the name ``{value}`` already exists.', 'error')
                await interaction.response.send_message(embed=embed)
                return
            self.data[value] = self.data.pop(map_name)
            if self.cached_messages.get(map_name):
                self.cached_messages[value] = self.cached_messages.pop(map_name)
            embed = response_embed(f'Successfully changed map name from ``{map_name}`` to ``{value}``', 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(value, interaction)
        elif field == 'sections':
            sections = []
            section_names = [x.strip() for x in value.split(';') if x.strip() != '']
            for section in section_names:
                players = []
                colon_ind = section.find(':')
                section_name = section
                if colon_ind != -1:
                    players = [x.strip() for x in section[(colon_ind+1):].split(',')]
                    section_name = section[:colon_ind]
                sections.append({'name': section_name, 'players': players, 'role': -1})
            self.data[map_name]['sections'] = sections
            message = f'Successfully set sections of map **{map_name}**: \n```\n'
            message += '\n'.join(section_names)
            message += '```'
            embed = response_embed(message, 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        elif field == 'progress start':
            found = False
            for section in self.data[map_name]['sections']:
                if section['name'].lower() == value.lower():
                    self.data[map_name]['progress_start'] = self.data[map_name]['sections'].index(section)
                    found = True
                    message = f'Successfully changed progress starting section to ``{section["name"]}`` for map **{map_name}**'
                    embed = response_embed(message, 'success', title='Field changed')
                    await interaction.response.send_message(embed=embed)
                    self.save()
                    await self.update_messages(map_name, interaction)
            if not found:
                message = f'Couldn\'t set progress starting section to {value} because that section doesn\'t seem to exist.'
                embed = response_embed(message, 'error')
                await interaction.response.send_message(embed=embed)
        elif field == 'emoji':
            self.data[map_name]['emoji'] = value
            embed = response_embed(f'Successfully set the emoji of a map **{map_name}** to {value}', 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        elif field == 'fails message':
            old_message = self.data[map_name]['fails_message']
            self.data[map_name]['fails_message'] = value
            if value != '-':
                message = f'Fails message of map **{map_name}** set to ``{value}``'
            else:
                message = f'Removed fails messages from map **{map_name}**'
            embed = response_embed(message, 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        elif field == 'no victors message':
            self.data[map_name]['no_victors_message'] = value
            if value != '-':
                message = f'No victors message of map **{map_name}** set to ``{value}``'
            else:
                message = f'Removed no victors message from map **{map_name}**'
            embed = response_embed(message, 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        elif field == 'starting section message':
            self.data[map_name]['starting_section_message'] = value
            if value != '-':
                message = f'Starting section message of map **{map_name}** set to ``{value}``'
            else:
                message = f'Starting section message for map **{map_name}** set to default.'
            embed = response_embed(message, 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        elif field == 'victor separators':
            if value != '-':
                separators = value.split(';')
                if separators[len(separators)-1] == '':
                    separators.pop()
                
                for separator in separators:
                    dates = list(datefinder.find_dates(separator, strict=True))
                    if len(dates) > 1:
                        embed = response_embed(f'Multiple dates found in ``{separator}``.', 'error')
                        await interaction.response.send_message(embed=embed)
                        return
                    elif len(dates) == 0:
                        embed = response_embed(f'Could not parse date from ``{separator}``. Every separator must include a date.', 'error')
                        await interaction.response.send_message(embed=embed)
                        return
                
                embed = response_embed(f'Set separators for map ``{map_name}``', 'success')
                await interaction.response.send_message(embed=embed)
                self.data[map_name]['victor_separators'] = separators
                self.save()
                await self.update_messages(map_name, interaction)
   
            else:
                embed = response_embed(f'Cleared all separators from map ``{map_name}``', 'success')
                await interaction.response.send_message(embed=embed)
                self.data[map_name]['victor_separators'] = []
                self.save()
                await self.update_messages(map_name, interaction)
        elif field == 'hide roles':
            self.data[map_name]['hide_roles'] = value
            message = f'Disabled showing role separators for map ``{map_name}``' if value else f'Enabled showing role separators for map ``{map_name}``'
            embed = response_embed(message, 'success', title='Field changed')
            await interaction.response.send_message(embed=embed)
            self.save()
            await self.update_messages(map_name, interaction)
        else:
            embed = response_embed('Unknown field. Please select a field from the autocomplete suggestions.', 'error')
            await interaction.response.send_message(embed=embed)
    
    @group.command(name='setrole', description='Set which role to give players when they reach a given section')
    async def setrole_command(self, interaction: discord.Interaction, map_name: str, section_name: str, role: discord.Role):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        if section_name == 'Victor':
            self.data[map_name]['victor_role'] = role.id
            self.save()
            embed = response_embed(f'Successfully set victor role ``@{role.name}`` for the map {map_name}', 'success', title='Role set')
            await interaction.response.send_message(embed=embed)
            await self.update_messages(map_name, interaction)
            return
        
        found = False
        for section in self.data[map_name]['sections']:
            if section['name'].lower() == section_name.lower():
                section['role'] = role.id
                found = True
                self.save()
                embed = response_embed(f'Successfully set role ``@{role.name}`` for section {section["name"]} for the map {map_name}', 'success', title='Role set')
                await interaction.response.send_message(embed=embed)
                await self.update_messages(map_name, interaction)
        if not found:
            embed = response_embed(f'Couldn\'t set role for section {section_name} because that section doesn\'t seem to exist', 'error')
            await interaction.response.send_message(embed=embed)
    
    @group.command(name='removerole', description='Remove role from a section of a map')
    async def removerole_command(self, interaction: discord.Interaction, map_name: str, section_name: str):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        if section_name == 'Victor':
            self.data[map_name]['victor_role'] = -1
            self.save()
            embed = response_embed(f'Successfully removed victor role from the map {map_name}', 'success', title='Role removed')
            await interaction.response.send_message(embed=embed)
            await self.update_messages(map_name, interaction)
            return
        
        found = False
        for section in self.data[map_name]['sections']:
            if section['name'].lower() == section_name.lower():
                section['role'] = -1
                found = True
                self.save()
                embed =response_embed(f'Successfully removed role from section {section["name"]} of the map {map_name}', 'success', title='Role removed')
                await interaction.response.send_message(embed=embed)
                await self.update_messages(map_name, interaction)
        if not found:
            embed = response_embed(f'Couldn\'t remove role from section {section_name} because that section doesn\'t seem to exist', 'error')
            await interaction.response.send_message(embed=embed)
    
    @group.command(name='send', description='Sends a map message to the specified channel')
    async def send_command(self, interaction: discord.Interaction, map_name: str, channel: discord.TextChannel):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        messages = await self.build_map_messages(map_name, interaction.guild)
        
        discord_messages = []
        self.data[map_name]['messages'] = []
        self.cached_messages[map_name] = []
        for message in messages:
            m = await channel.send(message)
            discord_messages.append(m)
            msg_obj = {'guild': str(m.guild.id), 'channel': str(m.channel.id), 'message': str(m.id)}
            self.data[map_name]['messages'].append(msg_obj)
            self.cached_messages[map_name].append(m)
            
        message = f'{len(discord_messages)} messages sent: https://discord.com/channels/{discord_messages[0].guild.id}/{discord_messages[0].channel.id}/{discord_messages[0].id}'
        embed = response_embed(message, 'success')
        self.save()
        await interaction.response.send_message(embed=embed)
    
    @group.command(name='list', description='Show a list of all registered maps')
    async def list_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title='List of registered maps', color=discord.Color.gold())
        message = ''
        for map_name, map in self.data.items():
            if len(map['messages']) != 0:
                guild_id = map['messages'][0]['guild']
                channel_id = map['messages'][0]['channel']
                message_id = map['messages'][0]['message']
                if guild_id == -1 or channel_id == -1 or message_id == -1:
                    link = 'No message set'
                else:
                    link = f'https://discord.com/channels/{guild_id}/{channel_id}/{message_id}'
            else:
                link = '``Not sent``'
            message += f'**{map_name}:** {link}\n'
        message = message[:len(message)-1]
        
        message = message[:3999]
        
        embed.description = message
        await interaction.response.send_message(embed=embed)
    
    @group.command(name='update', description='Force update messages of a map')
    async def update_command(self, interaction: discord.Interaction, map_name: str):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return
        
        await interaction.response.defer()
        await self.update_messages(map_name, interaction)
        await interaction.followup.send(embed=response_embed('Messages updated', 'success'))
     
    @group.command(name='printsections', description='Get sections of a map including players for convenient editing')
    async def printsections_command(self, interaction: discord.Interaction, map_name: str):
        if not self.data.get(map_name):
            embed = response_embed(f'Couldn\'t find a registered map with the name {map_name}', 'error')
            await interaction.response.send_message(embed=embed)
            return

        msg = ''
        for section in self.data[map_name]['sections']:
            msg += section['name']
            if len(section['players']) > 0:
                msg += ': ' + section['players'][0]
                for player in section['players'][1:]:
                    msg += ',' + player
            msg += ';\n'
        msg = msg[:(len(msg)-2)]
        
        await interaction.response.send_message(f'```{msg}```')
    
    @group.command(name='reload', description='Reload data from file')
    async def reload_command(self, interaction: discord.Interaction):
        self.load()
        await interaction.response.send_message('reloaded')
     
    @send_command.autocomplete('map_name')
    @edit_command.autocomplete('map_name')
    @printsections_command.autocomplete('map_name')
    @update_command.autocomplete('map_name')
    @setrole_command.autocomplete('map_name')
    @removerole_command.autocomplete('map_name')
    async def map_autocompletion(self, interaction: discord.Integration, current: str) -> typing.List[app_commands.Choice[str]]:
        map_choices = []
        for map in self.data:
            if current.lower() in map.lower():
                map_choices.append(app_commands.Choice(name=map, value=map))
                
        return map_choices[:25] 
    
    @edit_command.autocomplete('value')
    async def edit_autocompletion(self, interaction: discord.Integration, current: str) -> typing.List[app_commands.Choice[str]]:
        value_choices = []
        
        args = interaction.namespace
        
        if 'map_name' in args:
            if 'field' in args:
                if args['field'] == 'progress start':
                    if self.data.get(args['map_name']):
                        value_choices = [app_commands.Choice(name=x['name'], value=x['name']) for x in self.data[args['map_name']]['sections']]
                if args['field'] == 'hide roles':
                    value_choices = [app_commands.Choice(name='True', value=True), app_commands.Choice(name='False', value=False)]
        real_choices = []
        for choice in value_choices:
            if current.lower() in choice.name.lower():
                real_choices.append(choice)
        
        return real_choices[:25] 
            
    @setrole_command.autocomplete('section_name')
    @removerole_command.autocomplete('section_name')
    async def setrole_autocompletion(self, interaction: discord.Integration, current: str) -> typing.List[app_commands.Choice[str]]:
        args = interaction.namespace
        
        choices = [app_commands.Choice(name='Victor', value='Victor')]
        
        if 'map_name' in args:
            if self.data.get(args['map_name']):
                choices += [app_commands.Choice(name=x['name'], value=x['name']) for x in self.data[args['map_name']]['sections']]
        
        real_choices = []
        for choice in choices:
            if current.lower() in choice.name.lower():
                real_choices.append(choice)
        
        return real_choices[:25]  
    
    async def set_progress(self, ign: str, map_name: str, section_name: str, interaction: discord.Interaction):
        response = {'error': 0, 'old_progress': '', 'new_progress': '', 'removed_roles': [], 'given_roles': []}
        
        if not self.data.get(map_name):
            response['error'] = -1
            return response
        
        players = self.bot.get_cog('Players')
        if not players:
            response['error'] = -3
            return response
        
        if section_name != '-':
            section = None
            for x in self.data[map_name]['sections']:
                if x['name'] == section_name:
                    section = x
                    break
             
            if not section:
                response['error'] = -2
                return response
        else:
            response['new_progress'] = 'No progress'
        
        roles_to_remove = []
        roles_to_add = []
        victor_role = interaction.guild.get_role(self.data[map_name]['victor_role'])
        if victor_role:
            roles_to_remove.append(victor_role)
        
        response['old_progress'] = 'No progress'
        for sec in self.data[map_name]['sections']:
            if ign in sec['players']:
                try: 
                    sec['players'].remove(ign)
                    response['old_progress'] = sec['name']
                except ValueError: pass
            if sec['role'] != -1:
                role = interaction.guild.get_role(sec['role'])
                if role:
                    roles_to_remove.append(role)
        for victor in self.data[map_name]['victors']:
            if victor['name'] == ign:
                self.data[map_name]['victors'].remove(victor)
                response['old_progress'] = 'Victor'
        
        if section_name != '-':
            section['players'].append(ign)
            response['new_progress'] = section['name']
            
            index = self.data[map_name]['sections'].index(section)
            for i in range(len(self.data[map_name]['sections'][:(index+1)])):
                sec = self.data[map_name]['sections'][i]
                if sec['role'] != -1:
                    role = interaction.guild.get_role(sec['role'])
                    if role:
                        roles_to_add = [role]
            
        self.save()
        await self.update_messages(map_name, interaction)
        
        player = players.get_player(ign=ign)
        member = None
        if player['id'] != '-1':
            member = await interaction.guild.fetch_member(player['id'])
        
        if member:
            actual_roles_to_remove = []
            for role in roles_to_remove:
                if member.get_role(role.id) and not role in roles_to_add:
                    actual_roles_to_remove.append(role) 
            
            actual_roles_to_add = []
            for role in roles_to_add:
                if not member.get_role(role.id):
                    if role in actual_roles_to_remove:
                        actual_roles_to_remove.remove(role)
                    else:
                        actual_roles_to_add.append(role)
               
            await member.remove_roles(*actual_roles_to_remove)
            await member.add_roles(*actual_roles_to_add)
            response['removed_roles'] = actual_roles_to_remove
            response['given_roles'] = actual_roles_to_add
        
        return response
    
    async def add_victor(self, ign: str, map_name: str, fails: int, date: str, interaction: discord.Interaction):
        response = {'error': 0, 'old_progress': '', 'new_progress': 'Victor', 'removed_roles': [], 'given_roles': []}
        
        if not self.data.get(map_name):
            response['error'] = -1
            return response
        
        roles_to_remove = []
        roles_to_add = []
        
        players = self.bot.get_cog('Players')
        if not players:
            response['error'] = -3
            return response
        
        victor_role = interaction.guild.get_role(self.data[map_name]['victor_role'])
        if victor_role:
            roles_to_add.append(victor_role)
        
        response['old_progress'] = 'No progress'
        for sec in self.data[map_name]['sections']:
            if ign in sec['players']:
                try: 
                    response['old_progress'] = sec['name']
                    sec['players'].remove(ign)
                except ValueError: pass
            if sec['role'] != -1:
                role = interaction.guild.get_role(sec['role'])
                if role:
                    roles_to_remove.append(role)
        
        for victor in self.data[map_name]['victors']:
            if victor['name'] == ign:
                self.data[map_name]['victors'].remove(victor)
                response['old_progress'] = 'Victor'
        
        player = players.get_player(ign=ign)
        member = None
        if player['id'] != '-1':
            member = await interaction.guild.fetch_member(player['id'])
        
        if member:
            actual_roles_to_remove = []
            for role in roles_to_remove:
                if member.get_role(role.id) and not role in roles_to_add:
                    actual_roles_to_remove.append(role) 
            
            actual_roles_to_add = []
            for role in roles_to_add:
                if not member.get_role(role.id):
                    if role in actual_roles_to_remove:
                        actual_roles_to_remove.remove(role)
                    else:
                        actual_roles_to_add.append(role)
            
            await member.remove_roles(*actual_roles_to_remove)
            await member.add_roles(*actual_roles_to_add)
            response['removed_roles'] = actual_roles_to_remove
            response['given_roles'] = actual_roles_to_add
        
        self.data[map_name]['victors'].append({'name': ign, 'date': date, 'fails': fails})
        self.save()
        await self.update_messages(map_name, interaction)
        
        return response
    
    async def update_messages(self, map_name: str, interaction: discord.Interaction):
        if not self.data.get(map_name):
            return
        
        old_ids = self.data[map_name]['messages']
        old_messages = []
        if not map_name in self.cached_messages:
            self.cached_messages[map_name] = []
            for ids in old_ids:
                guild_id = ids['guild']
                channel_id = ids['channel']
                message_id = ids['message']
                message = await self.fetch_message(guild_id, channel_id, message_id)
                if not message:
                    await interaction.channel.send(response_embed('Could not edit messages because one was not found.', 'error'))
                    return
                old_messages.append(message)
                self.cached_messages[map_name].append(message)
        else:
            old_messages = []
            for m in self.cached_messages[map_name]:
                old_messages.append(m)
                            
        messages = await self.build_map_messages(map_name, interaction.guild)

        '''
        if len(messages) < len(old_messages):
            await interaction.channel.send(embed=response_embed('Empty message was deleted.', 'information'))
            while len(messages) < len(old_messages):
                old_message = old_messages.pop()
                self.cached_messages[map_name].pop()
                await old_message.delete()
                self.data[map_name]['messages'].pop()
            self.save()
        elif len(messages) > len(old_messages):
            await interaction.channel.send(embed=response_embed('All messages in that channel exceeded character limit so a new message was sent. If it was sent wrongly delete all the messages and use ``/map send`` again.', 'information'))
            while len(messages) > len(old_messages):
                new_msg = await old_messages[0].channel.send('temporary message because discord doesn\'t allow sending empty messages')
                old_messages.append(new_msg)
                self.cached_messages[map_name].append(new_msg)
                self.data[map_name]['messages'].append({'guild': str(new_msg.guild.id), 'channel': str(new_msg.channel.id), 'message': str(new_msg.id)})
            self.save()  
        '''
        if (len(messages) != len(old_messages)):
            link = f'https://discord.com/channels/{old_messages[0].guild.id}/{old_messages[0].channel.id}/{old_messages[0].id}'
            await interaction.channel.send(embed=response_embed(f'Messages in {link} reached character limit so the update was cancelled. Delete the messages and use ``/map send`` again when necessary.', 'error'))
            return
        
        for i in range(len(messages)):
            try:
                if old_messages[i].content != messages[i]:
                    await old_messages[i].edit(content=messages[i])
            except discord.HTTPException as e: 
                await interaction.channel.send(embed=response_embed(f'HTTPException: ``{e}`` (message id: ``{old_messages[i].id}``). Most likely one of the messages was forcefully deleted, use ``/map send`` again.', 'error'))
                return
            
    async def fetch_message(self, guild_id, channel_id, message_id):
        guild = await self.bot.fetch_guild(guild_id)
        if not guild:
            return None
        channel = await guild.fetch_channel(channel_id)
        if not channel:
            return None
        message = await channel.fetch_message(message_id)
        if not message:
            return None
        
        return message 
    
    async def build_map_messages(self, map_name: str, guild: discord.Guild):        
        map = self.data[map_name]
        emoji = f'{map["emoji"]}'
        players = self.bot.get_cog('Players')
        if not players:
            return
        
        message = ''
        line_limit = 1850
        line_dashes = '-------------------------------------------'
        line_equals = '===================================='
        splits = ['SPLIT_PRIORITY_1', 'SPLIT_PRIORITY_2']
        
        def remove_formatting(str: str):
            clean_str = ''
            for c in str:
                if c in ['_']:
                    clean_str += '\\'
                clean_str += c
            return clean_str
        
        if map_name != 'Magnum Opus':
            if len(map['sections']) > 0:
                for section in map['sections'][:map['progress_start']]:
                    message += f'\n*{remove_formatting(section["name"])}*' 
                
                message += splits[1]
                if map["starting_section_message"] != '-':
                    message += f'\n{line_equals}\n'
                    message += f'**{map_name}** {map["starting_section_message"]}'
                    message += f'\n{line_equals}'
                
                for section in map['sections'][map['progress_start']:]:
                    if not map.get('hide_roles'):
                        if section['role'] != -1:
                            message += splits[1]
                            message += f'\n{line_dashes}\n'
                            message += f'<@&{section["role"]}>'
                            message += f'\n{line_dashes}'
                    
                    message += f'\n**{remove_formatting(section["name"])}**:'
                    if len(section['players']) > 0:
                        message += f' {remove_formatting(section["players"][0])}'
                        for player in section['players'][1:]:
                            player = players.get_player(player)
                            
                            if not player:
                                mes = f'An unregistered player ``{player}`` is listed in map ``{map_name}``'
                                embed = response_embed(mes, 'information')
                                await guild.get_channel(1200045616781328425).send(embed=embed)
                            message += f', {remove_formatting(player["ign"])}'
                        message += f' {emoji}'
            
            self.sort_victors(map_name)
            message += splits[0]
            message += f'\n{line_equals}\n'
            role_id = self.data[map_name]["victor_role"]
            role = f'<@&{role_id}>' if role_id != -1 else f'**{map_name}** Victor'
            message += f'{emoji} {role} {emoji}'
            message += f'\n{line_equals}'
            #messages[len(messages)-1] += f'\n🗓️ **__Released on {map["release_date"]}__** 🗓️'
            
            separators = []
            for separator in map['victor_separators']:
                datelist = list(datefinder.find_dates(separator, strict=True))
                if len(datelist) > 0:
                    date = datelist[0]
                else:
                    date = datetime.datetime(2000, 1, 10)
                separators.append({'date': date, 'text': separator})        
            separators.sort(key=lambda x: x['date'])
            
            if len(separators) > 0:
                message += f'\n🗓️ **__{separators[0]["text"]}__** 🗓️'
                separators.pop(0)

            i = 1
            if len(map['victors']) > 0:
                for victor in map['victors']:
                    player = players.get_player(victor["name"])
                    
                    if not player:
                        mes = f'An unregistered player ``{victor["name"]}`` is listed in map ``{map_name}``'
                        embed = response_embed(mes, 'information')
                        await guild.get_channel(1200045616781328425).send(embed=embed)
                    flag_msg = ''
                    flag_emoji = discord.utils.get(guild.emojis, name=f'flag_{player["country_code"]}')
                    if flag_emoji:
                        flag_msg = str(flag_emoji)
                    else:
                        flag_msg = f':flag_{player["country_code"]}:'			
                    message += f'\n{i}. **{remove_formatting(victor["name"])}** ({victor["date"]}) {flag_msg}'
                    if map['fails_message'] != '-':
                        message +=  f' - *{victor["fails"]} {map["fails_message"]} fail'
                        if victor["fails"] != 1:
                            message += 's*'
                        else:
                            message += '*'

                    victor_date = datetime.datetime.strptime(victor['date'], '%b %d, %Y')
                    next_victor = map['victors'][i] if i < len(map['victors']) else None
                    next_victor_date = datetime.datetime.strptime(next_victor['date'], '%b %d, %Y') if next_victor else None
                    if len(separators) > 0:
                        while len(separators) > 0 and separators[0]['date'] > victor_date and (not next_victor_date or separators[0]['date'] <= next_victor_date):
                            message += splits[1]
                            message += f'\n\n🗓️ **__{separators[0]["text"]}__** 🗓️'
                            separators.pop(0)
                                            
                    i += 1

            else:
                for separator in separators:
                    message += f'\n🗓️ **__{separator["text"]}__** 🗓️'
                message += '\n**0 Victors**'
                if map['no_victors_message'] != '-':
                    message += f' - *{map["no_victors_message"]}*'
            
            if map_name == 'Endurance Hall':
                message += '\n\n*:star2: Note: Every section is l/d or semi-l/d to the start of the map or further back in the rank*'
            '''       
            sections = re.split(f'(\n{line_equals}\n|\n{line_dashes}\n|\n🗓️[^🗓️\n]*🗓️\n)', message)
            fixed_sections = []
            for section in sections
                if len(section) < 1999:
                    fixed_sections.append(section)
                else:
                    fixed_sections += section.splitlines(True)
            
            sections = fixed_sections
            
            
            #lines = message.splitlines(True)
            
            
            messages = ['']
            flags = 0
            for i in range(len(sections)):
                flags += emoji_count(sections[i])*10
                if len(messages[len(messages)-1]) + len(sections[i]) + flags < 1999:
                    messages[len(messages)-1] += sections[i]
                else:
                    messages.append(sections[i])      
            '''  
            
            messages = [message]
            
            if len(messages[0]) >= 1800:
                messages = messages[0].split(splits[0])
            
            new_messages = []
            for msg in messages:
                if len(msg) < 1800:
                    new_messages.append(msg)
                else:
                    split_msg = ['']
                    temp_splits = msg.split(splits[1])
                    for split in temp_splits:
                        if len(split_msg[len(split_msg)-1]) + len(split) < 1800:
                            split_msg[len(split_msg)-1] += split
                        else:
                            split_msg.append(split)
                    new_messages += split_msg
            messages = list(filter(lambda a: a != '', new_messages))
            
            new_messages = []
            for msg in messages:
                if len(msg) < 1800:
                    new_messages.append(msg)
                else:
                    split_msg = ['']
                    temp_splits = msg.splitlines(True)
                    for split in temp_splits:
                        if len(split_msg[len(split_msg)-1]) + len(split) < 1800:
                            split_msg[len(split_msg)-1] += split
                        else:
                            split_msg.append(split)
                    new_messages += split_msg
            messages = list(filter(lambda a: a != '', new_messages))
            
            new_messages = []
            for msg in messages:
                clean_msg = msg
                for split in splits:
                    clean_msg = clean_msg.replace(split, '')
                if clean_msg[len(clean_msg)-1] == '\n':
                    clean_msg = clean_msg[:-1]
                new_messages.append(clean_msg)
            messages = new_messages
                            
            return messages
                
               
        else:
            messages = ['']
            # MAGNUP OPUS FORMATTING
            star_emojis = [ '<:02:1221434635582705735>',
                            '<:03:1221434636752912477>',
                            '<:04:1221434638908657694>',
                            '<:05:1221434640305225789>',
                            '<:06:1221434641677029436>',
                            '<:07:1221434642813423669>',
                            '<:08:1221434644646334495>',
                            '<:09:1221434646365995090>',
                            '<:10:1221526721283751946>',
                            '<:11:1221434741346275378>',
                            '<:12:1221434652498067496>',
                            '<:13:1221434656344248340>',
                            '<:14:1221434747180552263>',
                            '<:15:1221434659888566353>',
                            '<:16:1221434664300974131>',
                            '<:17:1221434666180018266>',
                            '<:18:1221434748765864007>']
            
            line_limit = 1300
            section_index = 1
            star_index = 0
            messages[0] += f'_{map["sections"][0]["name"]}\n\n'
            
            for machine_index in range(0, 15):
                if machine_index != 0:
                    if len(messages[len(messages)-1]) > line_limit:
                        messages.append('\n_ _\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~')
                    else:
                        messages[len(messages)-1] += '\n\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~'
                    messages[len(messages)-1] += f'\n{star_emojis[star_index]} **__{map["machines"][machine_index]}__** {star_emojis[star_index]}'
                    messages[len(messages)-1] += '\n------------------------------------'
                    star_index += 1
                else:
                    messages[len(messages)-1] += f'__{map["machines"][machine_index]}__'
                while map['sections'][section_index]['name'].startswith(f'M{machine_index+1}'):
                    if section_index <= map['progress_start']:
                        messages[len(messages)-1] += f'\n{map["sections"][section_index]["name"]}'
                    else:
                        section = map["sections"][section_index]
                        if str(section_index) in map['reverse_transitions']:
                            messages[len(messages)-1] += f'\n_{map["reverse_transitions"][str(section_index)]}_' 
                        if section['role'] != -1:
                            if not messages[len(messages)-1].endswith('-----'):
                                messages[len(messages)-1] += '\n------------------------------------'
                            messages[len(messages)-1] += f'\n<@&{section["role"]}>'
                            messages[len(messages)-1] += '\n------------------------------------'
                        messages[len(messages)-1] += f'\n**{section["name"]}**:'
                        
                        if len(section['players']) > 0:
                            messages[len(messages)-1] += f' {remove_formatting(section["players"][0])}'
                            for player in section['players'][1:]:
                                messages[len(messages)-1] += f', {remove_formatting(player)}'
                            messages[len(messages)-1] += f' {star_emojis[star_index]}'

                    if section_index == map['progress_start']:
                        messages[len(messages)-1] += '_'
                        messages[len(messages)-1] += '\n==============================\n'
                        messages[len(messages)-1] += f'**{map_name}** {map["starting_section_message"]}'
                        messages[len(messages)-1] += '\n=============================='
                    section_index += 1
            
            if len(messages[len(messages)-1]) > line_limit:
                messages.append('\n_ _\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~')
            else:
                messages[len(messages)-1] += '\n\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~'
            messages[len(messages)-1] += f'\n{star_emojis[star_index]} **__THE SHELVES__** {star_emojis[star_index]}'
            star_index += 1
            messages[len(messages)-1] += '\n------------------------------------'
            if len(messages[len(messages)-1]) > line_limit:
                messages.append('')
            for shelf_ind in range(4):
                section = map["sections"][section_index]
                messages[len(messages)-1] += f'\n<@&{map["sections"][section_index]["role"]}>:'
                section_index += 1
            
            if len(messages[len(messages)-1]) > line_limit:
                messages.append('\n_ _\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~')
            else:
                messages[len(messages)-1] += '\n\n~~⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ~~'
            messages[len(messages)-1] += f'\n{star_emojis[star_index]} **__SKY__** {star_emojis[star_index]}'
            star_index += 1
            messages[len(messages)-1] += '\n------------------------------------'
            for sky_ind in range(2):
                section = map["sections"][section_index]
                if section['role'] != -1:
                    if not messages[len(messages)-1].endswith('-----'):
                        messages[len(messages)-1] += '\n------------------------------------'
                    messages[len(messages)-1] += f'\n<@&{section["role"]}>'
                    messages[len(messages)-1] += '\n------------------------------------'
                messages[len(messages)-1] += f'\n**{map["sections"][section_index]["name"]}**:'
                section_index += 1
            
            self.sort_victors(map_name)
            if len(messages[len(messages)-1]) > line_limit:
                messages.append('\n_ _')
            messages[len(messages)-1] += '\n==============================\n'
            role_id = self.data[map_name]["victor_role"]
            role = f'<@&{role_id}>' if role_id != -1 else f'**{map_name}** Victor'
            messages[len(messages)-1] += f'{star_emojis[star_index]} {role} {star_emojis[star_index]}'
            messages[len(messages)-1] += '\n=============================='
            #messages[len(messages)-1] += f'\n🗓️ **__Released on {map["release_date"]}__** 🗓️'
            
            separators = []
            for separator in map['victor_separators']:
                date = list(datefinder.find_dates(separator, strict=True))[0]
                separators.append({'date': date, 'text': separator})        
            separators.sort(key=lambda x: x['date'])
            
            if len(separators) > 0:
                messages[len(messages)-1] += f'\n🗓️ **__{separators[0]["text"]}__** 🗓️'
                separators.pop(0)

            i = 1
            separator_i = 0
            if len(map['victors']) > 0:
                for victor in map['victors']:
                    player = players.get_player(victor["name"])
                    
                    flag_msg = ''
                    flag_emoji = discord.utils.get(guild.emojis, name=f'flag_{player["country_code"]}')
                    if flag_emoji:
                        flag_msg = str(flag_emoji)
                    else:
                        flag_msg = f':flag_{player["country_code"]}:'			
                    messages[len(messages)-1] += f'\n{i}. **{victor["name"]}** ({victor["date"]}) {flag_msg}'
                    if map['fails_message'] != '-':
                        messages[len(messages)-1] +=  f' - *{victor["fails"]} {map["fails_message"]} fail'
                        if victor["fails"] != 1:
                            messages[len(messages)-1] += 's*'
                        else:
                            messages[len(messages)-1] += '*'
                    
                    if len(messages[len(messages)-1]) > line_limit:
                        messages.append('')

                    victor_date = datetime.datetime.strptime(victor['date'], '%b %d, %Y')
                    next_victor = map['victors'][i] if i < len(map['victors']) else None
                    next_victor_date = datetime.datetime.strptime(next_victor['date'], '%b %d, %Y') if next_victor else None
                    if len(separators) > 0:
                        while len(separators) > 0 and separators[0]['date'] > victor_date and (not next_victor_date or separators[0]['date'] < next_victor_date):
                            messages[len(messages)-1] += f'\n\n🗓️ **__{separators[0]["text"]}__** 🗓️'
                            separators.pop(0)
                            if len(messages[len(messages)-1]) > line_limit:
                                messages.append('')
                                            
                    i += 1

            else:
                for separator in separators:
                    messages[len(messages)-1] += f'\n🗓️ **__{separator["text"]}__** 🗓️'
                    if len(messages[len(messages)-1]) > line_limit:
                            messages.append('')
                messages[len(messages)-1] += '\n**0 Victors**'
                if map['no_victors_message'] != '-':
                    messages[len(messages)-1] += f' - {map["no_victors_message"]}'
        
            if '' in messages: messages.remove('')
            return messages
    
    def sort_victors(self, map_name: str):
        victors = self.data[map_name]['victors']
        victors.sort(key=lambda victor: datetime.datetime.strptime(victor['date'], '%b %d, %Y'))
    
    def load(self):
        f = open('maps.json', 'r')
        json_obj = f.read()
        self.data = json.loads(json_obj)
        f.close()
        
    def save(self):
        json_obj = json.dumps(self.data, indent=4)
        f = open('maps.json', 'w')
        f.write(json_obj)
        f.close()

async def setup(bot):
    await bot.add_cog(Maps(bot))
