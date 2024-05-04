import discord
from discord import app_commands
from discord.ext import commands
import time
import json
from util import response_embed

class RoleList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_cooldown = 1000000000
        self.last_update = time.time_ns()
        self.data = {}
        self.load()
        self.cached_messages = {}
        self.guild = None
        self.progresser = None
        self.experienced = None
        
    group = app_commands.Group(name='rolelist', description="List of progress roles")
  
    @group.command(name='send', description='Send message with the list of roles to the specified channel')
    async def send_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        roles = self.get_roles(interaction.guild)
        messages = self.build_messages(roles)

        self.data['messages'] = []
        self.cached_messages = {}
        for msg in messages:
            discord_msg = await channel.send(msg)
            msg_ids = {"guild": discord_msg.guild.id, "channel": discord_msg.channel.id, "message": discord_msg.id}
            self.data['messages'].append(msg_ids)
            self.cached_messages[f'{msg_ids["guild"]}{msg_ids["channel"]}{msg_ids["message"]}'] = discord_msg
        self.save()

    @group.command(name='updateall', description='Go through every member and fix their Progresser and Experienced roles.')
    async def updateall_command(self, interaction: discord.Interaction):
        if interaction.guild.id == 913838786947977256:
            self.guild = interaction.guild
        else:
            await interaction.response.send_message('Woopsie', ephemeral=True)
            return
        
        if interaction.user.id != 269105396587823104:
            embed = response_embed("This command is very heavy and should not be used unless necessary so it's restricted to <@269105396587823104>", 'error')
            await interaction.response.send(embed=embed)
        
        self.prog_roles = self.get_roles(self.guild)
        if not self.progresser:
            self.progresser = self.guild.get_role(1211105309653737554)
        if not self.experienced:
            self.experienced = self.guild.get_role(987997064216588348)
        
        progresser_added_list = []
        progresser_removed_list = []
        experienced_added_list = []
        experienced_removed_list = []
            
        for member in interaction.guild.members:
            qualify_progresser = False
            qualify_experienced = False
            victor = False
            count = 0
            
            roles = member.roles
                        
            for role in roles:
                if role in self.prog_roles:
                    if not qualify_progresser:
                        qualify_progresser = True
                    
                    if not qualify_experienced:
                        count += 1
                        if "victor" in role.name.lower():
                            victor = True

                        if count >= 3 and victor:
                            qualify_experienced = True
            
            if not self.progresser in roles and qualify_progresser:
                progresser_added_list.append(f'<@{member.id}> ({member.name})')
                print(f'Progresser added: {member.name}')
                await member.add_roles(self.progresser)
                
            if self.progresser in roles and not qualify_progresser:
                progresser_removed_list.append(f'<@{member.id}> ({member.name})')
                print(f'Progresser removed: {member.name}')
                await member.remove_roles(self.progresser)
                
            if not self.experienced in roles and qualify_experienced:
                experienced_added_list.append(f'<@{member.id}> ({member.name})')
                print(f'Experienced removed: {member.name}')
                await member.add_roles(self.experienced)
                
            if self.experienced in roles and not qualify_experienced:
                experienced_removed_list.append(f'<@{member.id}> ({member.name})')
                print(f'Experienced added: {member.name}')
                await member.remove_roles(self.experienced)
        
        channel = interaction.channel
        await channel.send(embed=response_embed('\n'.join(progresser_added_list), 'information', 'Progresser role added'))
        await channel.send(embed=response_embed('\n'.join(progresser_removed_list), 'information', 'Progresser role removed'))
        await channel.send(embed=response_embed('\n'.join(experienced_added_list), 'information', 'Experienced role added'))
        await channel.send(embed=response_embed('\n'.join(experienced_removed_list), 'information', 'Experienced role removed'))
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.guild.id == 913838786947977256:
            self.guild = before.guild
        else:
            return
        
        self.prog_roles = self.get_roles(self.guild)
        if not self.progresser:
            self.progresser = self.guild.get_role(1211105309653737554)
        if not self.experienced:
            self.experienced = self.guild.get_role(987997064216588348)
        
        time_now = time.time_ns()
        if time_now - self.last_update < self.update_cooldown:
            return
        self.last_update = time_now
    
        await self.update_messages()
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild.id == 913838786947977256:
            self.guild = before.guild
        else:
            return
        
        self.prog_roles = self.get_roles(self.guild)
        if not self.progresser:
            self.progresser = self.guild.get_role(1211105309653737554)
        if not self.experienced:
            self.experienced = self.guild.get_role(987997064216588348)
        
        if len(before.roles) < len(after.roles):
            new_role = next(role for role in after.roles if role not in before.roles)
            if new_role in self.prog_roles:
                if not self.progresser in after.roles:
                    await after.add_roles(self.progresser)
                
                if not self.experienced in after.roles:
                    victor = False
                    count = 0
                    for role in after.roles:
                        if role in self.prog_roles:
                            count += 1
                            if "victor" in role.name.lower():
                                victor = True
                    if count >= 3 and victor:
                        await after.add_roles(self.experienced)
        elif len(before.roles) > len(after.roles):
            new_role = next(role for role in before.roles if role not in after.roles)
            if new_role in self.prog_roles:
                progresser = False
                experienced = False
                victor = False
                count = 0
                for role in after.roles:
                    if role in self.prog_roles:
                        progresser = True
                        count += 1
                        if "victor" in role.name.lower():
                            victor = True
                
                experienced = (count >= 3 and victor)
                
                            
                if self.progresser in after.roles and not progresser:
                    await after.remove_roles(self.progresser)
                
                if self.experienced in after.roles and not experienced:
                    await after.remove_roles(self.experienced)
                    
    
    async def update_messages(self):
        contents = self.build_messages(self.prog_roles)
        
        messages = []
        for msg_ids in self.data['messages']:
            if f'{msg_ids["guild"]}{msg_ids["channel"]}{msg_ids["message"]}' in self.cached_messages:
                messages.append(self.cached_messages[f'{msg_ids["guild"]}{msg_ids["channel"]}{msg_ids["message"]}'])
            else:
                discord_msg = await self.fetch_message(msg_ids['guild'], msg_ids['channel'], msg_ids['message'])
                if not discord_msg:
                    #await interaction.channel.send(response_embed('Could not edit messages because one was not found.', 'error'))
                    return
                messages.append(discord_msg)
                self.cached_messages[f'{msg_ids["guild"]}{msg_ids["channel"]}{msg_ids["message"]}'] = discord_msg
        
        for i in range(len(messages)):
            await messages[i].edit(content=contents[i])

 
    def get_roles(self, guild):
        roles = list(guild.roles)
        roles.reverse()
        
        booster_role = 942863357990547457
        odd_bathroom_roles = 1124817935643463890
        
        i = None
        j = None
        for role in roles:
            if role.id == booster_role:
                i = roles.index(role) + 1
            elif role.id == odd_bathroom_roles:
                j = roles.index(role)
        if not i or not j:
            return roles
        
        return roles[i:j]

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
    
    def build_messages(self, roles):
        messages = [roles[0].mention]
        for role in roles[1:]:
            messages[len(messages)-1] += f'\n{role.mention}'
            if len(messages[len(messages)-1]) > 1900:
                messages.append('')

        return messages
    
    def load(self):
        f = open('roles.json', 'r')
        json_obj = f.read()
        self.data = json.loads(json_obj)
        
    def save(self):
        json_obj = json.dumps(self.data, indent=4)
        f = open('roles.json', 'w')
        f.write(json_obj)
    
async def setup(bot):
  await bot.add_cog(RoleList(bot))