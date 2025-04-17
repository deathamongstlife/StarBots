from Star-Utils import Cog, CogsUtils
# Standard Imports
import asyncio
import re
import json

# Discord Imports
import discord

# starbot Imports
from starbot.core import commands, checks, utils, Config
from starbot.core.utils import chat_formatting
from starbot.core.utils.chat_formatting import box, escape

CODE_BLOCK_RE = re.compile(r"^((```.*)(?=\s)|(```))")
ERROR_PATTERN = re.compile(r'\ntest\.dmb.\S.(\d*)\s(error)')
WARNING_PATTERN = re.compile(r'\ntest\.dmb.\S.\d*\serrors,\s(\d*).(warning.)')
INCLUDE_PATTERN = re.compile(r'#(|\W+)include')

# imports and template are from Crossedfall/crossed-cogs and Red bot, many thanks! (no affiliation)


class Dmreply(Cog):
    def __init__(self, bot):
        
        self.bot = bot
        self.repo_tags = []
        self.config = Config.get_conf(self, identifier=806715409318936616, force_registration=True)
        
        self.config.register_global(
            defaultreply="Hi! This bot isn't set up to receive DMs yet. Please try sending your message in the server. Thanks!",
            defaultreplyfooter="This is an automated reply.",
        )

        default_guild = {
            "title": "DM from Bot Owner"
        }
        self.config.register_guild(**default_guild)

    # This cog does not store any End User Data
    async def red_get_data_for_user(self, *, user_id: int):
        return {}
    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        pass


    @commands.command()
    @checks.mod()
    async def dmreply(self, ctx, user_id: int, *, message: str):
        """Sends a DM to a user.

        Requires a User ID, or it won't work."""

        destination = self.bot.get_user(user_id)
        if destination is None or destination.bot:
            await ctx.send("Invalid ID, user not found, or user is a bot.")
            return

        description = await self.config.guild(ctx.guild).title()
        # content = _("You can reply to this message with {}contact").format(prefix)
        e = discord.Embed(color=(await ctx.embed_colour()), description=message)

        # e.set_footer(text=content)
        if ctx.bot.user.display_avatar.url:
            e.set_author(name=description, icon_url=ctx.bot.user.display_avatar.url)
        else:
            e.set_author(name=description)

        try:
            await destination.send(embed=e)
        except discord.HTTPException:
            await ctx.send("Sorry, I couldn't deliver your message")
        else:
            await ctx.send("Message delivered")


    @commands.guild_only()
    @commands.group()
    @commands.is_owner()
    async def setdmreply(self, ctx: commands.Context):
        """Change the configurations in dmreply (Owner only)
        
        Embed color is determined by your bot's settings under [p]set.
        Automatic reply embed color cannot be changed."""
        if not ctx.invoked_subcommand:
            pass

    @setdmreply.command(name="title")
    async def sdmtitle(self, ctx, *, message):
        """Change the embed title"""
        await self.config.guild(ctx.guild).title.set(message)
        await ctx.message.add_reaction("✅")

    @setdmreply.command(name="defaultreply")
    async def sdmdefaultreply(self, ctx, *, message):
        """Change the embed body/content"""
        await self.config.defaultreply.set(message)
        await ctx.message.add_reaction("✅")
        
    @setdmreply.command(name="defaultreplyfooter")
    async def sdmdefaultreplyfooter(self, ctx, *, message):
        """Change the embed footer text"""
        await self.config.defaultreplyfooter.set(message)
        await ctx.message.add_reaction("✅")

    @setdmreply.command(name="list")
    async def sdmlist(self, ctx):
        """List current settings"""

        # sending a dm
        title = await self.config.guild(ctx.guild).title()
        e = discord.Embed(color=(await ctx.embed_colour()), description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        if ctx.bot.user.display_avatar.url:
            e.set_author(name=title, icon_url=ctx.bot.user.display_avatar.url)
        else:
            e.set_author(name=title)

        # automatic reply
        defaultreply = await self.config.defaultreply()
        defaultreplyfooter = await self.config.defaultreplyfooter()
        
        dme = discord.Embed(color=16711680, description=defaultreply)
        dme.set_footer(text=defaultreplyfooter)

        if self.bot.user.display_avatar.url:
            dme.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
        else:
            dme.set_author(name=self.bot.user.name)

        try:
            await ctx.send("sending a dm", embed=e)
            await ctx.send("automatic reply", embed=dme)
        except discord.HTTPException:
            await ctx.send("Sorry, it looks like I might be missing some permissions...")

        # await ctx.send(title)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild:
            return
        if message.author.bot:
            return
        if isinstance(message.channel, discord.abc.PrivateChannel):
            defaultreply = await self.config.defaultreply()
            defaultreplyfooter = await self.config.defaultreplyfooter()
            
            e = discord.Embed(color=16711680, description=defaultreply)
            e.set_footer(text=defaultreplyfooter)

            if self.bot.user.display_avatar.url:
                e.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
            else:
                e.set_author(name=self.bot.user.name)

            await message.author.send(embed=e)
        else:
            return
