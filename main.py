
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
import json
import asyncio
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
PING_CHANNEL_ID = int(os.getenv("PING_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
CONFIG = {
    'colors': {
        'E': 0x808080,  # Gray
        'D': 0x8B4513,  # Brown
        'C': 0x00FF00,  # Green
        'B': 0x0000FF,  # Blue
        'A': 0x800080,  # Purple
        'S': 0xFF4500,  # Orange Red
        'SS': 0xFF0000  # Red
    },
    'role_mentions': {
        'S': '@Raid-Team',
        'SS': '@Elite-Raiders'
    },
    'cooldown_seconds': 5,
    'max_dungeons_per_hour': 10
}

# In-memory storage (replace with database in production)
dungeon_history = []
user_preferences = {}
dungeon_stats = {'total_spawns': 0, 'rank_counts': {}, 'island_counts': {}}
last_alert_time = {}

@bot.event
async def on_ready():
    logger.info(f'Bot is now running as {bot.user}')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected to {len(bot.guilds)} guilds')

def get_rank_color(rank):
    """Get color for dungeon rank"""
    return CONFIG['colors'].get(rank.upper(), 0x5865F2)

def parse_dungeon_info(message_content):
    """Parse dungeon information from YAML-style format with error handling"""
    try:
        dungeon_data = {
            'island': 'Unknown',
            'map': 'Unknown',
            'boss': 'Unknown',
            'rank': 'E',
            'red_dungeon': 'No',
            'double_dungeon': 'No'
        }

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
                    dungeon_data[key] = 'Yes' if '✅' in value or 'yes' in value.lower() else 'No'
                else:
                    dungeon_data[key] = value

        return dungeon_data
    except Exception as e:
        logger.error(f"Error parsing dungeon info: {e}")
        return None

def is_duplicate_dungeon(dungeon_info):
    """Check if dungeon is a duplicate from recent history"""
    try:
        current_time = datetime.now()
        for historical_dungeon in dungeon_history[-20:]:  # Check last 20 dungeons
            time_diff = (current_time - historical_dungeon['timestamp']).total_seconds()
            if time_diff < 300:  # 5 minutes
                if (historical_dungeon['island'] == dungeon_info['island'] and 
                    historical_dungeon['boss'] == dungeon_info['boss'] and
                    historical_dungeon['rank'] == dungeon_info['rank']):
                    return True
        return False
    except Exception as e:
        logger.error(f"Error checking duplicate: {e}")
        return False

def should_alert_user(user_id, dungeon_info):
    """Check if user should receive alert based on preferences"""
    try:
        prefs = user_preferences.get(user_id, {})
        
        # Check rank filter
        if 'rank_filter' in prefs:
            allowed_ranks = prefs['rank_filter']
            if dungeon_info['rank'].upper() not in allowed_ranks:
                return False
        
        # Check red dungeon filter
        if 'red_only' in prefs and prefs['red_only']:
            if dungeon_info['red_dungeon'].lower() != 'yes':
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error checking user preferences: {e}")
        return True

def update_statistics(dungeon_info):
    """Update dungeon spawn statistics"""
    try:
        dungeon_stats['total_spawns'] += 1
        
        rank = dungeon_info['rank'].upper()
        dungeon_stats['rank_counts'][rank] = dungeon_stats['rank_counts'].get(rank, 0) + 1
        
        island = dungeon_info['island']
        dungeon_stats['island_counts'][island] = dungeon_stats['island_counts'].get(island, 0) + 1
    except Exception as e:
        logger.error(f"Error updating statistics: {e}")

def check_rate_limit(user_id):
    """Check if user is rate limited"""
    try:
        current_time = datetime.now()
        if user_id in last_alert_time:
            time_diff = (current_time - last_alert_time[user_id]).total_seconds()
            if time_diff < CONFIG['cooldown_seconds']:
                return False
        
        last_alert_time[user_id] = current_time
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True

async def create_dungeon_embed(dungeon_info, message_time=None):
    """Create a dungeon embed with error handling"""
    try:
        red_status = "✅ Yes" if dungeon_info['red_dungeon'].lower() in ['yes', 'true', '1'] else "❌ No"
        double_status = "✅ Yes" if dungeon_info['double_dungeon'].lower() in ['yes', 'true', '1'] else "❌ No"

        embed = discord.Embed(
            title=f"🎯 NEW DUNGEON ALERT — RANK {dungeon_info['rank'].upper()} 🌐",
            description="✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
            color=get_rank_color(dungeon_info['rank']))

        stats_text = f"```yaml\n🌍 Island        : {dungeon_info['island']}\n🗺️ Map           : {dungeon_info['map']}\n👹 Boss          : {dungeon_info['boss']}\n🏅 Rank          : {dungeon_info['rank'].upper()}\n🔥 Red Dungeon   : {red_status}\n⚔️ Double Dungeon: {double_status}\n```"
        embed.add_field(name="📊 Dungeon Information", value=stats_text, inline=False)

        community_text = ("🙏 **Thanks for playing!**\n"
                          "You're part of the Ascented community! 🆙\n\n")
        embed.add_field(name="🎮 Community", value=community_text, inline=False)

        time_str = message_time.strftime("%d/%m/%Y, %H:%M:%S") if message_time else datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        embed.add_field(name="🕒 Time", value=time_str, inline=False)

        embed.set_footer(text="Follow to get this channel's updates in your own server.")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1377893772729385040/1377912101971955733/Copilot_20250530_113401.png?ex=683ab025&is=68395ea5&hm=003fe31f8cf823ad920c89df21093f918f584018f2f48eb2eec1f50e06314200&")

        return embed
    except Exception as e:
        logger.error(f"Error creating embed: {e}")
        return None

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return

        if message.channel.id == GENERAL_CHANNEL_ID:
            ping_channel = bot.get_channel(PING_CHANNEL_ID)
            if not ping_channel:
                logger.error("Ping channel not found")
                return

            content_lower = message.content.lower()
            has_dungeon_indicators = (
                "spawned" in content_lower or
                ("🌍" in message.content and "🗺️" in message.content and "👹" in message.content)
            )

            if has_dungeon_indicators:
                dungeon_info = parse_dungeon_info(message.content)
                if not dungeon_info:
                    logger.warning("Failed to parse dungeon info")
                    return

                # Check for duplicates
                if is_duplicate_dungeon(dungeon_info):
                    logger.info("Duplicate dungeon detected, skipping")
                    return

                # Update statistics
                update_statistics(dungeon_info)

                # Add to history
                dungeon_history.append({
                    **dungeon_info,
                    'timestamp': datetime.now(),
                    'message_id': message.id
                })

                # Create embed
                embed = await create_dungeon_embed(dungeon_info, message.created_at)
                if not embed:
                    logger.error("Failed to create embed")
                    return

                # Add role mentions for high-rank dungeons
                mention_text = ""
                rank = dungeon_info['rank'].upper()
                if rank in CONFIG['role_mentions']:
                    mention_text = CONFIG['role_mentions'][rank]

                await ping_channel.send(content=mention_text, embed=embed)
                logger.info(f"Sent dungeon alert for {rank} rank dungeon on {dungeon_info['island']}")

    except Exception as e:
        logger.error(f"Error in on_message: {e}")

    await bot.process_commands(message)

@bot.command(name='commands')
async def help_command(ctx):
    """Show help information"""
    try:
        embed = discord.Embed(
            title="🤖 Dungeon Bot Commands",
            description="Here are all available commands:",
            color=0x5865F2
        )
        
        commands_text = """
        `!dungeon <rank> <island> <city> <map> <alienship> <boss> <red> <double>`
        Create a custom dungeon alert
        
        `!alert <rank> <island> <city> <map> <alienship> <boss> <red> <double>`
        Quick dungeon alert with space-separated values
        
        `!preferences set rank_filter <ranks>`
        Set which ranks you want to be notified about (e.g., S,SS)
        
        `!preferences set red_only true/false`
        Only get alerts for red dungeons
        
        `!preferences view`
        View your current preferences
        
        `!stats`
        View dungeon spawn statistics
        
        `!history [count]`
        View recent dungeon history (default: 5)
        """
        
        embed.add_field(name="📋 Commands", value=commands_text, inline=False)
        embed.add_field(name="📊 Ranks", value="E, D, C, B, A, S, SS", inline=False)
        
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await ctx.send("❌ Error displaying help information.")

@bot.command(name='preferences')
async def preferences_command(ctx, action=None, setting=None, *, value=None):
    """Manage user preferences"""
    try:
        user_id = ctx.author.id
        
        if action == "view":
            prefs = user_preferences.get(user_id, {})
            if not prefs:
                await ctx.send("You have no preferences set. Use `!commands` to see available options.")
                return
                
            embed = discord.Embed(title="Your Preferences", color=0x5865F2)
            for key, val in prefs.items():
                embed.add_field(name=key.replace('_', ' ').title(), value=str(val), inline=False)
            await ctx.send(embed=embed)
            
        elif action == "set" and setting and value:
            if user_id not in user_preferences:
                user_preferences[user_id] = {}
                
            if setting == "rank_filter":
                ranks = [r.strip().upper() for r in value.split(',')]
                valid_ranks = ['E', 'D', 'C', 'B', 'A', 'S', 'SS']
                ranks = [r for r in ranks if r in valid_ranks]
                user_preferences[user_id]['rank_filter'] = ranks
                await ctx.send(f"✅ Rank filter set to: {', '.join(ranks)}")
                
            elif setting == "red_only":
                user_preferences[user_id]['red_only'] = value.lower() == 'true'
                await ctx.send(f"✅ Red-only filter set to: {value.lower() == 'true'}")
                
            else:
                await ctx.send("❌ Invalid setting. Use `rank_filter` or `red_only`.")
        else:
            await ctx.send("❌ Usage: `!preferences view` or `!preferences set <setting> <value>`")
            
    except Exception as e:
        logger.error(f"Error in preferences command: {e}")
        await ctx.send("❌ Error managing preferences.")

@bot.command(name='stats')
async def stats_command(ctx):
    """Show dungeon spawn statistics"""
    try:
        embed = discord.Embed(title="📊 Dungeon Statistics", color=0x5865F2)
        embed.add_field(name="Total Spawns", value=dungeon_stats['total_spawns'], inline=True)
        
        if dungeon_stats['rank_counts']:
            rank_text = '\n'.join([f"{rank}: {count}" for rank, count in sorted(dungeon_stats['rank_counts'].items())])
            embed.add_field(name="Ranks", value=rank_text, inline=True)
        
        if dungeon_stats['island_counts']:
            top_islands = sorted(dungeon_stats['island_counts'].items(), key=lambda x: x[1], reverse=True)[:5]
            island_text = '\n'.join([f"{island}: {count}" for island, count in top_islands])
            embed.add_field(name="Top Islands", value=island_text, inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await ctx.send("❌ Error retrieving statistics.")

@bot.command(name='history')
async def history_command(ctx, count: int = 5):
    """Show recent dungeon history"""
    try:
        if not dungeon_history:
            await ctx.send("No dungeon history available.")
            return
            
        count = min(count, 10)  # Limit to 10
        recent_dungeons = dungeon_history[-count:]
        
        embed = discord.Embed(title=f"📜 Recent Dungeon History ({len(recent_dungeons)})", color=0x5865F2)
        
        for i, dungeon in enumerate(reversed(recent_dungeons), 1):
            time_str = dungeon['timestamp'].strftime("%H:%M:%S")
            value = f"🌍 {dungeon['island']} | 👹 {dungeon['boss']} | 🏅 {dungeon['rank'].upper()}"
            embed.add_field(name=f"{i}. {time_str}", value=value, inline=False)
        
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in history command: {e}")
        await ctx.send("❌ Error retrieving history.")

@bot.command(name='dungeon')
async def create_dungeon_alert(ctx, rank="E", island="XZ", city="", map_name="", alienship="", boss="Paitama", red_dungeon="No", double_dungeon="No"):
    """Create a custom dungeon alert"""
    try:
        if not check_rate_limit(ctx.author.id):
            await ctx.send("⏰ Please wait before creating another alert.")
            return

        dungeon_info = {
            'island': island,
            'map': map_name,
            'boss': boss,
            'rank': rank,
            'red_dungeon': red_dungeon,
            'double_dungeon': double_dungeon
        }

        embed = await create_dungeon_embed(dungeon_info)
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Error creating dungeon alert.")
            
    except Exception as e:
        logger.error(f"Error in dungeon command: {e}")
        await ctx.send("❌ Error creating dungeon alert.")

@bot.command(name='alert')
async def create_quick_alert(ctx, *, dungeon_info):
    """Create a dungeon alert with space-separated values"""
    try:
        if not check_rate_limit(ctx.author.id):
            await ctx.send("⏰ Please wait before creating another alert.")
            return

        parts = dungeon_info.split()
        if len(parts) < 2:
            await ctx.send("❌ Please provide at least rank and island. Use `!commands` for usage.")
            return

        dungeon_data = {
            'rank': parts[0] if len(parts) > 0 else "E",
            'island': parts[1] if len(parts) > 1 else "XZ",
            'map': parts[3] if len(parts) > 3 else "",
            'boss': parts[5] if len(parts) > 5 else "Paitama",
            'red_dungeon': parts[6] if len(parts) > 6 else "No",
            'double_dungeon': parts[7] if len(parts) > 7 else "No"
        }

        embed = await create_dungeon_embed(dungeon_data)
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Error creating dungeon alert.")

    except Exception as e:
        logger.error(f"Error in alert command: {e}")
        await ctx.send("❌ Error creating alert. Please use format: `!alert <rank> <island> ...`")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!commands` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")

bot.run(TOKEN)
