import discord
from discord.ext import commands

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.BAD_WORDS = ["badword1", "badword2", "stupid", "dumb"]  # Add more here
        self.LOG_CHANNEL_ID = 123456789012345678  # Replace with your actual log channel ID

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        msg_lower = message.content.lower()
        found_bad = [word for word in self.BAD_WORDS if word in msg_lower]

        if found_bad:
            try:
                await message.delete()

                log_channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 Bad Word Detected",
                        description=(
                            f"**User:** {message.author.mention}\n"
                            f"**Channel:** {message.channel.mention}\n"
                            f"**Message:** ||{message.content}||"
                        ),
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="AutoMod System")
                    await log_channel.send(embed=embed)

            except discord.Forbidden:
                print("⚠️ Missing permission to delete messages or send logs.")
            except discord.HTTPException as e:
                print(f"❌ Error deleting message or sending log: {e}")

        # ✅ This ensures your commands still work
        await self.bot.process_commands(message)

def setup(bot):
    bot.add_cog(AutoMod(bot))
