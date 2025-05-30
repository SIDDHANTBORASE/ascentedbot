import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
PING_CHANNEL_ID = int(os.getenv("PING_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Bot is now running as {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guilds')


def parse_dungeon_info(message_content):
    """Parse dungeon information from YAML-style format"""
    import re
    
    # Default values
    dungeon_data = {
        'island': 'Unknown',
        'map': 'Unknown', 
        'boss': 'Unknown',
        'rank': 'E',
        'red_dungeon': 'No',
        'double_dungeon': 'No'
    }
    
    # Extract information using regex patterns
    patterns = {
        'island': r'🌍\s*Island\s*:\s*(.+)',
        'map': r'🗺️\s*Map\s*:\s*(.+)',
        'boss': r'👹\s*Boss\s*:\s*(.+)',
        'rank': r'🏅\s*Rank\s*:\s*(.+)',
        'red_dungeon': r'🔥\s*Red Dungeon\s*:\s*(.+)',
        'double_dungeon': r'⚔️\s*Double Dungeon\s*:\s*(.+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, message_content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key in ['red_dungeon', 'double_dungeon']:
                # Convert emoji format to Yes/No
                dungeon_data[key] = 'Yes' if '✅' in value or 'yes' in value.lower() else 'No'
            else:
                dungeon_data[key] = value
    
    return dungeon_data


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    if message.channel.id == GENERAL_CHANNEL_ID:
        ping_channel = bot.get_channel(PING_CHANNEL_ID)
        if ping_channel:
            # Check if message contains dungeon spawn information
            if "spawned" in message.content.lower() and "```yaml" in message.content:
                # Parse the dungeon information
                dungeon_info = parse_dungeon_info(message.content)
            else:
                # Use default values if no YAML format detected
                dungeon_info = {
                    'island': 'XZ',
                    'map': 'Unknown',
                    'boss': 'Paitama', 
                    'rank': 'E',
                    'red_dungeon': 'No',
                    'double_dungeon': 'No'
                }
            
            # Convert Yes/No to proper emoji format
            red_status = "✅ Yes" if dungeon_info['red_dungeon'].lower() in ['yes', 'true', '1'] else "❌ No"
            double_status = "✅ Yes" if dungeon_info['double_dungeon'].lower() in ['yes', 'true', '1'] else "❌ No"
            
            # Create rich embed
            embed = discord.Embed(
                title=f"🎯 NEW DUNGEON ALERT — RANK {dungeon_info['rank'].upper()} 🌐",
                description="✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
                color=0x5865F2
            )
            
            # Add dungeon stats
            stats_text = (
                f"🌍 **Island**: {dungeon_info['island']}\n"
                f"🏙️ **City**: Unknown\n"
                f"🗺️ **Map**: {dungeon_info['map']}\n"
                f"👽 **Alienship**: Unknown\n"
                f"👹 **Boss**: {dungeon_info['boss']}\n"
                f"🔥 **Rank**: {dungeon_info['rank'].upper()}\n"
                f"🔴 **Red Dungeon**: {red_status}\n"
                f"❌ **Double Dungeon**: {double_status}"
            )
            embed.add_field(name="📊 Dungeon Information", value=stats_text, inline=False)
            
            # Add community message
            community_text = (
                "🙏 **Thanks for playing!**\n"
                "You're part of the CL Games community! 🆙\n\n"
                "💖 **Support Us!**\n"
                "Don't forget to like ⭐ and favorite 🏠 the game on Roblox!\n"
                "💎 Every bit of support helps us grow!"
            )
            embed.add_field(name="🎮 Community", value=community_text, inline=False)
            
            # Add timestamp
            current_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            embed.add_field(name="🕒 Time", value=current_time, inline=False)
            
            # Set footer
            embed.set_footer(text="Follow to get this channel's updates in your own server.")
            
            # Set thumbnail (you can replace with your game's icon URL)
            embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
            
            await ping_channel.send(embed=embed)

    await bot.process_commands(message)


@bot.command(name='dungeon')
async def create_dungeon_alert(ctx, rank="E", island="XZ", city="", map_name="", alienship="", boss="Paitama", red_dungeon="No", double_dungeon="No"):
    """Create a custom dungeon alert
    Usage: !dungeon <rank> <island> <city> <map> <alienship> <boss> <red_dungeon> <double_dungeon>
    Example: !dungeon S Tokyo MainCity CentralMap AlienShip1 DragonLord Yes No
    """
    # Convert Yes/No to proper emoji format
    red_status = "✅ Yes" if red_dungeon.lower() in ['yes', 'true', '1'] else "❌ No"
    double_status = "✅ Yes" if double_dungeon.lower() in ['yes', 'true', '1'] else "❌ No"
    
    embed = discord.Embed(
        title=f"🎯 NEW DUNGEON ALERT — RANK {rank.upper()} 🌐",
        description="✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
        color=0x5865F2
    )
    
    stats_text = (
        f"🌍 **Island**: {island}\n"
        f"🏙️ **City**: {city}\n"
        f"🗺️ **Map**: {map_name}\n"
        f"👽 **Alienship**: {alienship}\n"
        f"👹 **Boss**: {boss}\n"
        f"🔥 **Rank**: {rank.upper()}\n"
        f"🔴 **Red Dungeon**: {red_status}\n"
        f"❌ **Double Dungeon**: {double_status}"
    )
    embed.add_field(name="📊 Dungeon Information", value=stats_text, inline=False)
    
    community_text = (
        "🙏 **Thanks for playing!**\n"
        "You're part of the CL Games community! 🆙\n\n"
        "💖 **Support Us!**\n"
        "Don't forget to like ⭐ and favorite 🏠 the game on Roblox!\n"
        "💎 Every bit of support helps us grow!"
    )
    embed.add_field(name="🎮 Community", value=community_text, inline=False)
    
    current_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    embed.add_field(name="🕒 Time", value=current_time, inline=False)
    
    embed.set_footer(text="Follow to get this channel's updates in your own server.")
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
    
    await ctx.send(embed=embed)


@bot.command(name='alert')
async def create_quick_alert(ctx, *, dungeon_info):
    """Create a dungeon alert with space-separated values
    Usage: !alert <rank> <island> <city> <map> <alienship> <boss> <red_dungeon> <double_dungeon>
    Example: !alert S Tokyo MainCity CentralMap AlienShip1 DragonLord Yes No
    """
    try:
        parts = dungeon_info.split()
        
        # Set defaults if not enough parameters provided
        rank = parts[0] if len(parts) > 0 else "E"
        island = parts[1] if len(parts) > 1 else "XZ"
        city = parts[2] if len(parts) > 2 else ""
        map_name = parts[3] if len(parts) > 3 else ""
        alienship = parts[4] if len(parts) > 4 else ""
        boss = parts[5] if len(parts) > 5 else "Paitama"
        red_dungeon = parts[6] if len(parts) > 6 else "No"
        double_dungeon = parts[7] if len(parts) > 7 else "No"
        
        # Convert Yes/No to proper emoji format
        red_status = "✅ Yes" if red_dungeon.lower() in ['yes', 'true', '1'] else "❌ No"
        double_status = "✅ Yes" if double_dungeon.lower() in ['yes', 'true', '1'] else "❌ No"
        
        embed = discord.Embed(
            title=f"🎯 NEW DUNGEON ALERT — RANK {rank.upper()} 🌐",
            description="✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
            color=0x5865F2
        )
        
        stats_text = (
            f"🌍 **Island**: {island}\n"
            f"🏙️ **City**: {city}\n"
            f"🗺️ **Map**: {map_name}\n"
            f"👽 **Alienship**: {alienship}\n"
            f"👹 **Boss**: {boss}\n"
            f"🔥 **Rank**: {rank.upper()}\n"
            f"🔴 **Red Dungeon**: {red_status}\n"
            f"❌ **Double Dungeon**: {double_status}"
        )
        embed.add_field(name="📊 Dungeon Information", value=stats_text, inline=False)
        
        community_text = (
            "🙏 **Thanks for playing!**\n"
            "You're part of the CL Games community! 🆙\n\n"
            "💖 **Support Us!**\n"
            "Don't forget to like ⭐ and favorite 🏠 the game on Roblox!\n"
            "💎 Every bit of support helps us grow!"
        )
        embed.add_field(name="🎮 Community", value=community_text, inline=False)
        
        current_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        embed.add_field(name="🕒 Time", value=current_time, inline=False)
        
        embed.set_footer(text="Follow to get this channel's updates in your own server.")
        embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error creating alert. Please use format: `!alert <rank> <island> <city> <map> <alienship> <boss> <red_dungeon> <double_dungeon>`")


bot.run(TOKEN)
