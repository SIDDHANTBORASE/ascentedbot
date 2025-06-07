import os
import discord
from discord.ext import commands
from datetime import datetime
import json
import asyncio
import logging
import re

from keep_alive import keep_alive
from discord.ui import View, Button

keep_alive()
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
PING_CHANNEL_ID = int(os.getenv("PING_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True  # needed for categories and roles

bot = commands.Bot(command_prefix='/', intents=intents)

# Configuration
CONFIG = {
    'colors': {
        'E': 0x808080,
        'D': 0x8B4513,
        'C': 0x00FF00,
        'B': 0x0000FF,
        'A': 0x800080,
        'S': 0xFF4500,
        'SS': 0xFF0000
    },
    'role_mentions': {
        'S': 1366005331758682289,
        'SS': 1366005331758682288
    },
    'cooldown_seconds': 5,
    'max_dungeons_per_hour': 10,

    # ===== TICKET CONFIG =====
    'ticket': {
        'category_id': 1366005332492550195,  # Replace with your ticket category ID
        'log_channel_id': 1378594826672541764,  # Replace with your log channel ID (optional)
        'staff_role_id': 1366005331809013943  # Replace with your staff role ID
    }
}

dungeon_history = []
user_preferences = {}
dungeon_stats = {'total_spawns': 0, 'rank_counts': {}, 'island_counts': {}}
last_alert_time = {}

##############################
# Dungeon Bot functions below (unchanged from your code)
##############################


@bot.event
async def on_ready():
    logger.info(f'Bot is now running as {bot.user}')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    await bot.load_extension("automod")

def get_rank_color(rank):
    return CONFIG['colors'].get(rank.upper(), 0x5865F2)


def parse_dungeon_info(message_content):
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
                    dungeon_data[
                        key] = 'Yes' if '✅' in value or 'yes' in value.lower(
                        ) else 'No'
                else:
                    dungeon_data[key] = value

        return dungeon_data
    except Exception as e:
        logger.error(f"Error parsing dungeon info: {e}")
        return None


def is_duplicate_dungeon(dungeon_info):
    try:
        current_time = datetime.now()
        for historical_dungeon in dungeon_history[-20:]:
            time_diff = (current_time -
                         historical_dungeon['timestamp']).total_seconds()
            if time_diff < 300:
                if (historical_dungeon['island'] == dungeon_info['island']
                        and historical_dungeon['boss'] == dungeon_info['boss']
                        and historical_dungeon['rank']
                        == dungeon_info['rank']):
                    return True
        return False
    except Exception as e:
        logger.error(f"Error checking duplicate: {e}")
        return False


def should_alert_user(user_id, dungeon_info):
    try:
        prefs = user_preferences.get(user_id, {})
        if 'rank_filter' in prefs:
            allowed_ranks = prefs['rank_filter']
            if dungeon_info['rank'].upper() not in allowed_ranks:
                return False
        if 'red_only' in prefs and prefs['red_only']:
            if dungeon_info['red_dungeon'].lower() != 'yes':
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking user preferences: {e}")
        return True


def update_statistics(dungeon_info):
    try:
        dungeon_stats['total_spawns'] += 1
        rank = dungeon_info['rank'].upper()
        dungeon_stats['rank_counts'][rank] = dungeon_stats['rank_counts'].get(
            rank, 0) + 1
        island = dungeon_info['island']
        dungeon_stats['island_counts'][
            island] = dungeon_stats['island_counts'].get(island, 0) + 1
    except Exception as e:
        logger.error(f"Error updating statistics: {e}")


def check_rate_limit(user_id):
    try:
        current_time = datetime.now()
        if user_id in last_alert_time:
            time_diff = (current_time -
                         last_alert_time[user_id]).total_seconds()
            if time_diff < CONFIG['cooldown_seconds']:
                return False
        last_alert_time[user_id] = current_time
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True


async def create_dungeon_embed(dungeon_info, message_time=None):
    try:
        red_status = "✅ Yes" if dungeon_info['red_dungeon'].lower() in [
            'yes', 'true', '1'
        ] else "❌ No"
        double_status = "✅ Yes" if dungeon_info['double_dungeon'].lower() in [
            'yes', 'true', '1'
        ] else "❌ No"

        embed = discord.Embed(
            title=
            f"🎯 NEW DUNGEON ALERT — RANK {dungeon_info['rank'].upper()} 🌐",
            description=
            "✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
            color=get_rank_color(dungeon_info['rank']))

        stats_text = f"```yaml\n🌍 Island        : {dungeon_info['island']}\n🗺️ Map           : {dungeon_info['map']}\n👹 Boss          : {dungeon_info['boss']}\n🏅 Rank          : {dungeon_info['rank'].upper()}\n🔥 Red Dungeon   : {red_status}\n⚔️ Double Dungeon: {double_status}\n```"
        embed.add_field(name="📊 Dungeon Information",
                        value=stats_text,
                        inline=False)

        community_text = (
            "🙏 **Thanks for Joining Us!**\nYou're part of the Ascented community! 🆙\n\n"
        )
        embed.add_field(name="🎮 Community", value=community_text, inline=False)

        time_str = message_time.strftime(
            "%d/%m/%Y, %H:%M:%S") if message_time else datetime.now().strftime(
                "%d/%m/%Y, %H:%M:%S")
        embed.add_field(name="🕒 Time", value=time_str, inline=False)

        embed.set_footer(text="Ascented Guild.")
        embed.set_thumbnail(url="")

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
            msg_channel = bot.get_channel(GENERAL_CHANNEL_ID)
            ping_channel = bot.get_channel(PING_CHANNEL_ID)
            if not ping_channel:
                logger.error("Ping channel not found")
                return

            content_lower = message.content.lower()
            has_dungeon_indicators = ("spawned" in content_lower
                                      or ("🌍" in message.content
                                          and "🗺️" in message.content
                                          and "👹" in message.content))

            if has_dungeon_indicators:
                dungeon_info = parse_dungeon_info(message.content)
                if not dungeon_info:
                    logger.warning("Failed to parse dungeon info")
                    return

                if is_duplicate_dungeon(dungeon_info):
                    logger.info("Duplicate dungeon detected, skipping")
                    return

                update_statistics(dungeon_info)

                dungeon_history.append({
                    **dungeon_info, 'timestamp':
                    datetime.now(),
                    'message_id':
                    message.id
                })

                embed = await create_dungeon_embed(dungeon_info,
                                                   message.created_at)
                if not embed:
                    logger.error("Failed to create embed")
                    return

                # Build ping message based on 4 conditions
                mention_text = f"<@&{1366005331758682291}>\n"

                rank = dungeon_info['rank'].upper()
                is_red = dungeon_info['red_dungeon'].lower() == 'yes'
                is_double = dungeon_info['double_dungeon'].lower() == 'yes'

                if rank == "S" and "S" in CONFIG['role_mentions']:
                    role = CONFIG['role_mentions']['S']
                    mention_text += f"<@&{role}>\n" if isinstance(
                        role, int) else f"{role}\n"

                if rank == "SS" and "SS" in CONFIG['role_mentions']:
                    role = CONFIG['role_mentions']['SS']
                    mention_text += f"<@&{role}>\n" if isinstance(
                        role, int) else f"{role}\n"

                if is_red:
                    mention_text += f"🔥 <@&{1366005331758682290}>\n"

                if is_double:
                    mention_text += f"⚔️<@&{1366005331758682286}>\n"

                await msg_channel.send("Embed sent to Dungeon channel")
                await ping_channel.send(content=mention_text or None,
                                        embed=embed)
                logger.info(
                    f"Sent dungeon alert for {rank} rank dungeon on {dungeon_info['island']}"
                )
    except Exception as e:
        logger.error(f"Error in on_message: {e}")
    
    await bot.process_commands(message)


@bot.command(name='commands')
async def help_command(ctx):
    """Show help information"""
    try:
        embed = discord.Embed(title="🤖 Dungeon Bot Commands",
                              description="Here are all available commands:",
                              color=0x5865F2)

        commands_text = """
        `/preferences set rank_filter <ranks>`
        Set which ranks you want to be notified about (e.g., S,SS)

        `/preferences set red_only true/false`
        Only get alerts for red dungeons

        `/preferences view`
        View your current preferences

        `/stats`
        View dungeon spawn statistics

        `/history [count]`
        View recent dungeon history (default: 5)

        `/pingdungeon <island> <world>`
        Create a custom dungeon alert

        `/bossalert <island> <world> <boss>`
        Use for boss alerts

        `/ticketpanel`
        (Admin) Post the ticket creation panel
        """

        embed.add_field(name="📋 Commands", value=commands_text, inline=False)
        embed.add_field(name="📊 Ranks",
                        value="E, D, C, B, A, S, SS",
                        inline=False)

        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await ctx.send("❌ Error displaying help information.")


##############################
# ===== TICKET SYSTEM BELOW =====
##############################


@bot.command(name="ticketpguild")
@commands.has_permissions(administrator=True)
async def ticket_p_guild(ctx):
    view = View()
    view.add_item(Button(label="🎟 Apply for Guild", style=discord.ButtonStyle.green, custom_id="open_ticket_guild"))

    embed = discord.Embed(
        title="Guild Joining Ticket",
        description=(
            "# Open Ticket For Joining the Guild:\n"
            "Please make sure to carefully read the guidelines in <#1366005332270387280>.\n"
            "Ensure you meet all the requirements listed before opening a ticket.\n"
            "To open a ticket, simply click the **button attached** to this message.\n"
            "Our team will assist you as soon as possible.\n"
            "Thank you for your interest in joining our community!"
        ),
        color=0x2ECC71
    )
    embed.set_footer(text="Ascended Sword")
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/1378594850383069235/1379694254393266227/image.png"
    )
    await ctx.send(embed=embed, view=view)


@bot.command(name="ticketpannel")
@commands.has_permissions(administrator=True)
async def ticket_pannel(ctx):
    view = View()
    view.add_item(Button(label="🎟 Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_support"))

    embed = discord.Embed(
        title="Support Section",
        description=(
            "If you're facing any issues or need assistance, please click the **button attached** to this message "
            "to open a support ticket. Our team will get back to you as soon as possible to help resolve your query.\n"
            "For faster assistance, kindly provide clear details or screenshots if applicable.\n"
            "Thank you for being a part of our community!"
        ),
        color=0x2ECC71
    )
    embed.set_footer(text="Ascended Sword")
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/1378594850383069235/1379694254393266227/image.png"
    )
    await ctx.send(embed=embed, view=view)


@bot.command(name="ttpannel")
@commands.has_permissions(administrator=True)
async def t_t_pannel(ctx):
    view = View()
    view.add_item(Button(label="🎟 Appoint Your Therapy Now", style=discord.ButtonStyle.green, custom_id="open_ticket_theoro"))

    embed = discord.Embed(
        title="Therapy Section",
        description=(
            "If you are having any mental health issues or something similar, please click the button attached to "
            "this message to open a support ticket. <@&1371118384179318795> will help you solve your problem as soon "
            "as possible. Please don’t leave your ticket empty. Thank you for being a part of our community!"
        ),
        color=0x2ECC71
    )
    embed.set_footer(text="Ascended Sword")
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/1378594850383069235/1379694254393266227/image.png"
    )
    await ctx.send(embed=embed, view=view)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CONFIG['ticket']['category_id'])
        staff_role = guild.get_role(CONFIG['ticket']['staff_role_id'])
        log_channel = bot.get_channel(CONFIG['ticket']['log_channel_id'])

        if custom_id in ["open_ticket_guild", "open_ticket_support", "open_ticket_theoro"]:
            # Check if ticket already exists
            existing = discord.utils.get(
                guild.text_channels,
                name=f"ticket-{interaction.user.name.lower()}")
            if existing:
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {existing.mention}",
                    ephemeral=True)
                return

            # Channel permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name.lower()}",
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user.name}"
            )

            # Embed content based on type
            if custom_id == "open_ticket_guild":
                description = (
                    f"{interaction.user.mention}, \nFor verification purposes, please send us screenshots of the following:\n"
                    f"• Gamepasses \n• DPS        :\n• Gems       :\n• Rank       :\n"
                    "Make sure the screenshots clearly show your username and the relevant details.\n"
                    "This will help us verify your eligibility quickly and accurately."
                )
            elif custom_id == "open_ticket_support":
                description = f"{interaction.user.mention}, wait for our staff to reach you soon."
            elif custom_id == "open_ticket_theoro":
                description = f"{interaction.user.mention}, our Therapist will reach out to you shortly."

            embed = discord.Embed(title="🎫 Ticket Opened", description=description, color=0x3498DB)
            embed.set_footer(text="Ascended Sword")
            embed.set_thumbnail(
                url="https://media.discordapp.net/attachments/1378594850383069235/1379694254393266227/image.png"
            )

            close_view = View()
            close_view.add_item(Button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket"))

            await channel.send(content=f"{interaction.user.mention} " , embed=embed)
            if custom_id == "open_ticket_theoro":
               await channel.send(content=f"<@&1371118384179318795>",view = close_view)
            elif custom_id == "open_ticket_guild":
                await channel.send(content =f"<@&1379102430746378240> <@&1379102625714147438>",view = close_view)
            else:
                await channel.send(content =f"<@&1379102430746378240> ",view = close_view)
            await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

            if log_channel:
                await log_channel.send(f"📩 Ticket opened by {interaction.user.mention} → {channel.mention}")

        elif custom_id == "close_ticket":
            await interaction.response.send_message("🛑 Ticket will be closed in 5 seconds...", ephemeral=True)
            await asyncio.sleep(5)
            if log_channel:
                await log_channel.send(f"🔒 Ticket closed: {interaction.channel.name} by {interaction.user.mention}")
            await interaction.channel.delete()



@bot.command(name='pdg')
async def p_d_g(ctx,
                       island: str,
                       world: str,
                       message_time: datetime = None):
    island = island.title()
    world = world.title()
    ping_channel = bot.get_channel(PING_CHANNEL_ID)
    mention_text = f"<@&{1366005331758682291}>"

    embed = discord.Embed(
        title=f"🎯 NEW DUNGEON ALERT 🌐",
        description=
        "✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
    )

    stats_text = f"```yaml\n🌍 Island        : {island}\n🗺️ World         : {world}```"

    embed.add_field(name="📊 Dungeon Information",
                    value=stats_text,
                    inline=False)

    community_text = (
        "🙏 **Thanks for Joining Us!**\nYou're part of the Ascented community! 🆙\n\n"
    )
    embed.add_field(name="🎮 Community", value=community_text, inline=False)

    time_str = message_time.strftime(
        "%d/%m/%Y, %H:%M:%S") if message_time else datetime.now().strftime(
            "%d/%m/%Y, %H:%M:%S")
    embed.add_field(name="🕒 Time", value=time_str, inline=False)

    embed.set_footer(text="Ascented Guild.")
    embed.set_thumbnail(url="")
    await ctx.send("Embed sent to Dungeon channel")
    await ping_channel.send(content=mention_text or None, embed=embed)
    logger.info(f"Sent dungeon alert for dungeon on {island}")


@bot.command(name='bossalert')
async def boss_alert(ctx,
                     island: str,
                     world: str,
                     boss: str,
                     message_time: datetime = None):
    island = island.title()
    world = world.title()
    boss = boss.title()
    ping_channel = bot.get_channel(PING_CHANNEL_ID)
    mention_text = f"<@&{1376068264454651964}>"

    embed = discord.Embed(
        title=f"🎯 NEW DUNGEON ALERT 🌐",
        description=
        "✨ A new dungeon has just spawned!\nPrepare your team and dive into battle!",
    )

    stats_text = f"```yaml\n🌍 Island        : {island}\n🗺️ World         : {world}\n👹 World Boss    : {boss}```"

    embed.add_field(name="📊 Dungeon Information",
                    value=stats_text,
                    inline=False)

    community_text = (
        "🙏 **Thanks for Joining Us!**\nYou're part of the Ascented community! 🆙\n\n"
    )
    embed.add_field(name="🎮 Community", value=community_text, inline=False)

    time_str = message_time.strftime(
        "%d/%m/%Y, %H:%M:%S") if message_time else datetime.now().strftime(
            "%d/%m/%Y, %H:%M:%S")
    embed.add_field(name="🕒 Time", value=time_str, inline=False)

    embed.set_footer(text="Ascented Guild.")
    embed.set_thumbnail(url="")
    await ping_channel.send(content=mention_text or None, embed=embed)
    logger.info(f"Sent Boss alert on {island}")


@bot.command(name='preferences')
async def preferences_command(ctx, action=None, setting=None, *, value=None):
    """Manage user preferences"""
    try:
        user_id = ctx.author.id

        if action == "view":
            prefs = user_preferences.get(user_id, {})
            if not prefs:
                await ctx.send(
                    "You have no preferences set. Use `!commands` to see available options."
                )
                return

            embed = discord.Embed(title="Your Preferences", color=0x5865F2)
            for key, val in prefs.items():
                embed.add_field(name=key.replace('_', ' ').title(),
                                value=str(val),
                                inline=False)
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
                await ctx.send(
                    f"✅ Red-only filter set to: {value.lower() == 'true'}")

            else:
                await ctx.send(
                    "❌ Invalid setting. Use `rank_filter` or `red_only`.")
        else:
            await ctx.send(
                "❌ Usage: `!preferences view` or `!preferences set <setting> <value>`"
            )

    except Exception as e:
        logger.error(f"Error in preferences command: {e}")
        await ctx.send("❌ Error managing preferences.")


@bot.command(name="createembed")
async def create_embed(ctx, channel_id: int, titlet: str, *, content: str):
    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("Invalid channel ID.")
            return
        contentn = f"\n {content}"
        embed = discord.Embed(title=titlet, color=0x5865F2)
        embed.add_field(name="Description", value=contentn, inline=False)
        embed.set_thumbnail(
            url=
            "https://media.discordapp.net/attachments/1378594850383069235/1379694254393266227/image.png?ex=68412be7&is=683fda67&hm=1d6b86035c182f79afb7515eef5a6ce5b19e418be52281eead63471687cb5825&=&format=webp&quality=lossless"
        )
        embed.set_footer(text="Ascented Guild.")

        await channel.send(embed=embed)
        await ctx.send("Embed sent successfully.")
    except Exception as e:
        await ctx.send(f"Error creating embed: {e}")


@bot.command(name='stats')
async def stats_command(ctx):
    """Show dungeon spawn statistics"""
    try:
        embed = discord.Embed(title="📊 Dungeon Statistics", color=0x5865F2)
        embed.add_field(name="Total Spawns",
                        value=dungeon_stats['total_spawns'],
                        inline=True)

        if dungeon_stats['rank_counts']:
            rank_text = '\n'.join([
                f"{rank}: {count}"
                for rank, count in sorted(dungeon_stats['rank_counts'].items())
            ])
            embed.add_field(name="Ranks", value=rank_text, inline=True)

        if dungeon_stats['island_counts']:
            top_islands = sorted(dungeon_stats['island_counts'].items(),
                                 key=lambda x: x[1],
                                 reverse=True)[:5]
            island_text = '\n'.join(
                [f"{island}: {count}" for island, count in top_islands])
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

        embed = discord.Embed(
            title=f"📜 Recent Dungeon History ({len(recent_dungeons)})",
            color=0x5865F2)

        for i, dungeon in enumerate(reversed(recent_dungeons), 1):
            time_str = dungeon['timestamp'].strftime("%H:%M:%S")
            value = f"🌍 {dungeon['island']} | 👹 {dungeon['boss']} | 🏅 {dungeon['rank'].upper()}"
            embed.add_field(name=f"{i}. {time_str}", value=value, inline=False)

        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in history command: {e}")
        await ctx.send("❌ Error retrieving history.")


@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            "❌ Command not found. Use `!commands` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")


bot.run(TOKEN)
