import discord

def response_embed(text: str, type: str, title: str = None, author: discord.Member = None):
    embed = discord.Embed(description=text)
    
    if title:
        embed.title = title
    
    if type == 'error':
        embed.color = discord.Color.red()
    elif type == 'success':
        embed.color = discord.Color.green()
    elif type == 'information':
        embed.color = discord.Color.yellow()
    else:
        return None
    
    if author:
        if author.avatar:
            embed.set_author(name=author.name, icon_url=author.avatar.url)
        else:
            embed.set_author(name=author.name)
    
    return embed

def align_string(text: str, length: int):
    space_count = length-len(text)
    
    if space_count <= 0:
        return text
    
    spaces = ''.join(([' '] * (space_count // 2)))
    
    text = '_' + spaces + '_' + text + '_' + spaces + '_'
    return text
