import discord
from starbot.core import commands, checks, Config
from Star-Utils import Cog
class InfiniCount(Cog):
    """Cog for creating a counting channel where only +1 increments are allowed."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

        default_guild = {
            "counting_channel_id": None,
            "previous_number": 0
        }

        self.config.register_guild(**default_guild)

    @commands.group()
    @commands.guild_only()
    async def infinicount(self, ctx):
        """Commands for managing InfiniCount."""
        pass

    async def counting_channel_exists(self, guild):
        counting_channel_id = await self.config.guild(guild).counting_channel_id()
        if counting_channel_id:
            channel = guild.get_channel(counting_channel_id)
            return channel is not None
        return False
    
    @infinicount.command(name="reset")
    @checks.admin_or_permissions(manage_channels=True)
    async def reset_count(self, ctx):
        """Reset the count in the counting channel."""
        guild = ctx.guild
        if await self.counting_channel_exists(guild):
            await self.config.guild(guild).previous_number.set(0)
            await ctx.send("Count has been reset to 0.")
        else:
            await ctx.send("No counting channel exists in this guild.")

    @infinicount.command(name="create")
    @checks.admin_or_permissions(manage_channels=True)
    async def create_counting_channel(self, ctx):
        """Create a counting channel where only +1 increments are allowed."""
        guild = ctx.guild
        if await self.counting_channel_exists(guild):
            return await ctx.send("A counting channel already exists in this guild.")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False),
            guild.me: discord.PermissionOverwrite(send_messages=True)
        }

        counting_channel = await guild.create_text_channel("InfiniCount", overwrites=overwrites)
        await self.config.guild(guild).counting_channel_id.set(counting_channel.id)
        await ctx.send("Counting channel created successfully.")

    @Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return

        counting_channel_id = await self.config.guild(message.guild).counting_channel_id()

        if counting_channel_id:
            channel = message.guild.get_channel(counting_channel_id)
            if channel and channel.id == message.channel.id:
                content = message.content
                previous_number = await self.config.guild(message.guild).previous_number()

                if not content.isdigit():
                    await message.delete()
                    await message.channel.send("Invalid input! Only numbers are allowed.", delete_after=3)
                    return

                number = int(content)

                if number != (previous_number + 1):
                    await message.delete()
                    await message.channel.send("Invalid number! Only +1 increments are allowed.", delete_after=3)
                    return

                await self.config.guild(message.guild).previous_number.set(number)

def setup(bot):
    bot.add_cog(InfiniCount(bot))
