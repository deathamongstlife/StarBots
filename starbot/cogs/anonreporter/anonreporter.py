from starbot.core import commands, checks, Config
from starbot.core.i18n import cog_i18n, Translator
from Star-Utils import Cog, CogsUtils

import discord
import asyncio
from typing import Optional

_ = Translator("AnonReporter", __file__)


@cog_i18n(_)
class AnonReporter(Cog):
    

    async def red_delete_data_for_user(self, *, user_id, requester):
        return  # This cog stores no EUD

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=171814082020, force_registration=True)
        default_guild = {"channel": None}
        default_global = {"rep_guild": None, "rep_channel": None}
        self.bot = bot
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    @checks.admin()
    @commands.group()
    async def anonreporter(self, ctx):
        """Anonreporter settings"""
        pass

    @commands.guild_only()
    @anonreporter.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel used for guild reports."""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(_("Report channel set to {channel}").format(channel=channel.mention))

    @commands.guild_only()
    @checks.is_owner()
    @anonreporter.command(name="global")
    async def global_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for global reports."""
        await self.config.rep_guild.set(ctx.guild.id)
        await self.config.rep_channel.set(channel.id)
        await ctx.send(
            _("Global reports channel set to {channel} in {guild}").format(
                channel=channel.mention, guild=ctx.guild.name
            )
        )

    @commands.command()
    async def anonreport(self, ctx, guild: Optional[discord.Guild], *, text: Optional[str]):
        """Report something anonymously (don't include text to report via DM)"""

        def msgcheck(m):
            return m.guild is None and m.author.id == ctx.author.id

        if not guild:
            if ctx.guild:
                guild = ctx.guild
            else:
                await ctx.send(_("You need to specify a guild."))
                return
        if not text:
            if channel := await self.config.guild(guild).channel():
                try:
                    await ctx.author.send(_("Send your report here. You have 120s."))
                    text = (
                        await self.bot.wait_for("message", check=msgcheck, timeout=120)
                    ).content
                except discord.HTTPException:
                    await ctx.send(
                        _("Sending a DM failed. Make sure you allow DMs from the bot."),
                        delete_after=15,
                    )
                except asyncio.TimeoutError:
                    await ctx.author.send(_("Action timed out."))
            else:
                await self._send_not_configured_correctly_message(ctx.channel)
                return
        else:
            if channel := await self.config.guild(guild).channel():
                await ctx.message.delete(delay=5)
            else:
                await self._send_not_configured_correctly_message(ctx.channel)
                return

        if 0 < len(text) < 1000:
            await guild.get_channel(channel).send(
                _("**New anonymous report:**\n{report}").format(report=text)
            )
            await ctx.tick()
        else:
            await ctx.send(_("Text too short or too long."), delete_after=15)

    @commands.command()
    async def botreport(self, ctx, text: str):
        """Report something to the bot owner anonymously."""
        await self.bot.get_guild(await self.config.rep_guild()).get_channel(
            await self.config.rep_channel()
        ).send(_("**New anonymous report:**\n{report}").format(report=text))
        await ctx.tick()

    async def _send_not_configured_correctly_message(self, messageable):
        await messageable.send(_("Anonreport is not configured correctly."), delete_after=15)
