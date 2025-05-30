import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
PING_CHANNEL_ID = int(os.getenv("PING_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot is now running as {client.user}')
    print(f'Bot ID: {client.user.id}')
    print(f'Connected to {len(client.guilds)} guilds')

@client.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == client.user:
        return

    if message.channel.id == GENERAL_CHANNEL_ID:
        ping_channel = client.get_channel(PING_CHANNEL_ID)
        if ping_channel:
            print(f"Forwarding message from {message.author.display_name}: {message.content}")
            await ping_channel.send(f"[From {message.author.display_name}]: {message.content}")

client.run(TOKEN)
