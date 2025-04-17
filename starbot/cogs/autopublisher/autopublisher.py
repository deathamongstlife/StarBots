from Star-Utils import Cog, CogsUtils
"""
MIT License

Copyright (c) 2022-present ltzmax

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import logging
import typing
from datetime import datetime, timedelta
from typing import Any, Dict, Final, List, Literal, Union

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starbot.core import Config, commands
from starbot.core.bot import Red
from starbot.core.utils.chat_formatting import box, humanize_list, humanize_number
from starbot.core.utils.views import ConfirmView
from tabulate import tabulate

from .utils import get_next_reset_timestamp

log = logging.getLogger("red.maxcogs.autopublisher")


class AutoPublisher(Cog):
    """Automatically push news channel messages."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.config: Config = Config.get_conf(self, identifier=15786223, force_registration=True)
        default_guild: Dict[str, Union[bool, List[int]]] = {
            "toggle": False,
            "ignored_channels": [],
        }
        default_global = {
            "published_count": 0,
            "published_weekly_count": 0,
            "published_monthly_count": 0,
            "published_yearly_count": 0,
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        # Schedule weekly count reset.
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            self.reset_count,
            "cron",
            day_of_week="sun",
            hour=0,
            minute=0,
            args=["weekly"],
        )
        scheduler.add_job(self.reset_count, "cron", day=1, hour=0, minute=0, args=["monthly"])
        scheduler.add_job(
            self.reset_count, "cron", month=1, day=1, hour=0, minute=0, args=["yearly"]
        )
        scheduler.start()
        self.logs = CogsUtils.get_logger("AutoPublisher")

    async def red_delete_data_for_user(self, **kwargs: Any) -> None:
        """Nothing to delete."""
        return

    async def increment_published_count(self):
        async with self.config.all() as data:
            data["published_count"] = data.get("published_count", 0) + 1
            data["published_weekly_count"] = data.get("published_weekly_count", 0) + 1
            data["published_monthly_count"] = data.get("published_monthly_count", 0) + 1
            data["published_yearly_count"] = data.get("published_yearly_count", 0) + 1

    async def reset_count(self, period: Literal["weekly", "monthly", "yearly"]) -> None:
        async with self.config.all() as data:
            if period == "weekly":
                data["published_weekly_count"] = 0
                log.info("Weekly published messages count has been reset.")
            if period == "monthly":
                data["published_monthly_count"] = 0
                log.info("Monthly published messages count has been reset.")
            if period == "yearly":
                data["published_yearly_count"] = 0
                log.info("Yearly published messages count has been reset.")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        """Automatically publish messages in news channels."""
        if message.guild is None:
            return

        isAutoPublisherEnabled = await self.config.guild(message.guild).toggle()
        ignoredChannels = await self.config.guild(message.guild).ignored_channels()
        isCogDisabled = await self.bot.cog_disabled_in_guild(self, message.guild)
        hasPermissions = (
            message.guild.me.guild_permissions.manage_messages
            and message.guild.me.guild_permissions.view_channel
        )
        isNewsFeatureEnabled = "NEWS" in message.guild.features
        isTextChannel = isinstance(message.channel, discord.TextChannel)
        isNewsChannel = isTextChannel and message.channel.is_news()

        if (
            not isAutoPublisherEnabled
            or message.channel.id in ignoredChannels
            or isCogDisabled
            or not hasPermissions
        ):
            return
        if not isNewsFeatureEnabled:
            if isAutoPublisherEnabled:
                await self.config.guild(message.guild).toggle.set(False)
                log.warning(
                    f"AutoPublisher has been disabled in {message.guild} due to News Channel feature not being enabled."
                )
            return
        if not isNewsChannel and isTextChannel:
            return
        if isTextChannel and isNewsChannel:
            try:
                await asyncio.sleep(0.5)
                await asyncio.wait_for(message.publish(), timeout=60)
                await self.increment_published_count()
            except (
                discord.HTTPException,
                discord.Forbidden,
                asyncio.TimeoutError,
            ) as e:
                log.error(e)

    @commands.guild_only()
    @commands.group(aliases=["aph", "autopub"])
    @commands.admin_or_permissions(manage_guild=True)
    async def autopublisher(self, ctx: commands.Context) -> None:
        """Manage AutoPublisher setting."""

    @commands.is_owner()
    @autopublisher.command(name="stats")
    async def _stats(self, ctx: commands.Context) -> None:
        """
        Show the number of published messages.
        """
        data = await self.config.all()

        total_published_messages = data.get("published_count", 0)
        weekly_published_messages = data.get("published_weekly_count", 0)
        monthly_published_messages = data.get("published_monthly_count", 0)
        yearly_published_messages = data.get("published_yearly_count", 0)

        now = datetime.utcnow()
        try:
            next_sunday_reset = await get_next_reset_timestamp(now, target_weekday=6)
            next_monthly_reset = await get_next_reset_timestamp(now, target_day=1)
            next_yearly_reset = await get_next_reset_timestamp(now, target_day=1, target_month=1)
        except (ValueError, TypeError) as e:
            log.error("Error getting next reset timestamp", exc_info=e)
            return

        table_data = [
            ["Total Weekly Published", humanize_number(weekly_published_messages)],
            ["Total Monthly Published", humanize_number(monthly_published_messages)],
            ["Total Yearly Published", humanize_number(yearly_published_messages)],
            ["Total Published Messages", humanize_number(total_published_messages)],
        ]
        msg_content = tabulate(table_data, headers=["Description", "Count"], tablefmt="simple")
        await ctx.send(
            f"{box(msg_content, lang='prolog')}\n"
            f"Next Weekly Reset: <t:{next_sunday_reset}:f> (<t:{next_sunday_reset}:R>)\n"
            f"Next Monthly Reset: <t:{next_monthly_reset}:f> (<t:{next_monthly_reset}:R>)\n"
            f"Next Yearly Reset: <t:{next_yearly_reset}:f> (<t:{next_yearly_reset}:R>)"
        )

    @autopublisher.command()
    @commands.bot_has_permissions(manage_messages=True, view_channel=True)
    async def toggle(self, ctx: commands.Context):
        """Toggle AutoPublisher enable or disable.

        - It's disabled by default.
            - Please ensure that the bot has access to `view_channel` in your news channels. it also need `manage_messages` to be able to publish.

        **Note:**
        - This cog requires News Channel. If you don't have it, you can't use this cog.
            - Learn more [here on how to enable](https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server) community server. (which is a part of news channel feature.)
        """
        if "NEWS" not in ctx.guild.features:
            view = discord.ui.View()
            style = discord.ButtonStyle.gray
            discordinfo = discord.ui.Button(
                style=style,
                label="Learn more here",
                url="https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server",
                emoji="<:icons_info:880113401207095346>",
            )
            view.add_item(item=discordinfo)
            return await ctx.send(
                f"Your server doesn't have News Channel feature. Please enable it first.",
                view=view,
            )
        await self.config.guild(ctx.guild).toggle.set(
            not await self.config.guild(ctx.guild).toggle()
        )
        toggle = await self.config.guild(ctx.guild).toggle()
        await ctx.send(f"AutoPublisher has been {'enabled' if toggle else 'disabled'}.")

    @autopublisher.command()
    async def ignorechannel(
        self, ctx: commands.Context, channels: commands.Greedy[discord.TextChannel]
    ):
        """
        Ignore/Unignore a news channel to prevent AutoPublisher from publishing messages in it.

        You can provide multiple channels to ignore or unignore at once.
        You decide if you wanna use the select menu or provide the channel(s) manually in the command.
        """
        if not "NEWS" in ctx.guild.features:
            view = discord.ui.View()
            style = discord.ButtonStyle.gray
            discordinfo = discord.ui.Button(
                style=style,
                label="Learn more here",
                url="https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server",
                emoji="<:icons_info:880113401207095346>",
            )
            view.add_item(item=discordinfo)
            return await ctx.send(
                f"Your server doesn't have News Channel feature. Please enable it first.",
                view=view,
            )

        # Check if there are any news channels
        news_channels = [channel for channel in ctx.guild.text_channels if channel.is_news()]
        if not news_channels:
            return await ctx.send("There are no news channels available to ignore.")

        # Add channels to ignore list
        ignored_channels = await self.config.guild(ctx.guild).ignored_channels()
        for channel in channels:
            # Check if the channel is a news channel
            if channel.is_news():
                if channel.id in ignored_channels:
                    ignored_channels.remove(channel.id)
                else:
                    ignored_channels.append(channel.id)
        await self.config.guild(ctx.guild).ignored_channels.set(ignored_channels)

        # Ensure the channel variable is defined
        if channels:
            # Filter out non-news channels
            news_channels = [channel for channel in channels if channel.is_news()]
            if news_channels:
                last_channel = news_channels[-1]
                await ctx.send(
                    f"News channel(s) has been {'ignored' if last_channel.id in ignored_channels else 'removed'}."
                )
            else:
                await ctx.send("No news channels were provided to ignore or remove.")
        else:
            view = IgnoredNewsChannelsView(self)
            view.ctx = ctx
            view.message = await ctx.send(
                "Select a news channel to ignore or remove.\n-# To unignore channel(s), Use `[p]autopublisher ignorechannel #channel(s)`.".replace(
                    "[p]", ctx.clean_prefix
                ),
                view=view,
            )

    @commands.bot_has_permissions(embed_links=True)
    @autopublisher.command(aliases=["view"])
    async def settings(self, ctx: commands.Context) -> None:
        """Show AutoPublisher setting."""
        data = await self.config.guild(ctx.guild).all()
        toggle = data["toggle"]
        channels = data["ignored_channels"]
        ignored_channels: List[str] = []
        for channel in channels:
            channel = ctx.guild.get_channel(channel)
            ignored_channels.append(channel.mention)
        msg = (
            f"AutoPublisher is currently {'enabled' if toggle else 'disabled'}.\n"
            f"Ignored channels: {humanize_list(ignored_channels) if ignored_channels else 'None'}"
        )
        embed = discord.Embed(
            title="AutoPublisher Setting",
            description=msg,
            color=await ctx.embed_color(),
        )
        await ctx.send(embed=embed)

    @autopublisher.command()
    async def reset(self, ctx: commands.Context) -> None:
        """Reset AutoPublisher setting."""
        view = ConfirmView(ctx.author, disable_buttons=True)
        view.message = await ctx.send(
            "Are you sure you want to reset AutoPublisher setting?", view=view
        )
        await view.wait()
        if view.result:
            await self.config.guild(ctx.guild).clear()
            await ctx.send("AutoPublisher setting has been reset.")
        else:
            await ctx.send("AutoPublisher setting reset has been cancelled.")

    @commands.is_owner()
    @autopublisher.command(hidden=True)  # To prevent accidental usage.
    @commands.bot_has_permissions(embed_links=True)
    async def resetcount(self, ctx: commands.Context) -> None:
        """Reset the published messages count."""
        view = ConfirmView(ctx.author, disable_buttons=True)
        embed = discord.Embed(
            title="Reset Published Messages Count",
            description="Are you sure you want to reset the published messages count?",
            color=await ctx.embed_color(),
        )
        embed.add_field(
            name="⚠️WARNING⚠️",
            value="This action will reset the published messages count to `0` and cannot be undone unless you have a backup of the data.",
            inline=False,
        )
        embed.set_footer(text="Be careful with this action.")
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.result:
            await self.config.published_count.set(0)
            await ctx.send("Published messages count has been reset.")
        else:
            await ctx.send("Published messages count reset has been cancelled.")


# -------------VIEW----------------
# Credit: Rosie.
# https://discord.com/channels/133049272517001216/133251234164375552/1280854205497737216
class IgnoredNewsChannelsView(discord.ui.View):
    def __init__(self, cog: Cog) -> None:
        super().__init__(timeout=180)
        self.cog: Cog = cog
        self.ctx: commands.Context = None
        self.message: discord.Message = None
        self.ignored_channels: typing.List[discord.ForumChannel] = []

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.ignored_channels: typing.List[discord.ForumChannel] = [
            channel
            for channel_id in await self.cog.config.guild(self.ctx.guild).ignored_channels()
            if (channel := self.ctx.guild.get_channel(channel_id))
        ]
        self.select.default_values = self.ignored_channels

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item: discord.ui.Item
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException as e:
            log.error(e)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.news],
        min_values=0,
        placeholder="Select the news channels to ignore.",
    )
    async def select(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ) -> None:
        await interaction.response.defer()
        selected_channels = select.values
        current_ignored_channels = await self.cog.config.guild(self.ctx.guild).ignored_channels()

        for channel in selected_channels:
            if channel.id in current_ignored_channels:
                current_ignored_channels.remove(channel.id)
            else:
                current_ignored_channels.append(channel.id)
        self.ignored_channels = [
            self.ctx.guild.get_channel(channel_id) for channel_id in current_ignored_channels
        ]

        await interaction.followup.send(
            f"Click on the button to Confirm the selected news channels.",
            ephemeral=True,
        )

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_ignored_channels = [channel.id for channel in self.ignored_channels]

        # Check if the channel is already ignored
        if new_ignored_channels == await self.cog.config.guild(self.ctx.guild).ignored_channels():
            return await interaction.response.send_message(
                "No changes were made because the selected news channel is already ignored.",
                ephemeral=True,
            )

        await self.cog.config.guild(self.ctx.guild).ignored_channels.set(new_ignored_channels)
        await interaction.response.send_message(
            ":white_check_mark: Ignored news channels saved!", ephemeral=True
        )
