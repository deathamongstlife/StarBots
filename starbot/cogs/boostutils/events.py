"""
MIT License

Copyright (c) 2024-present japandotorg

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

from typing import Any, Dict, List, Literal

import discord
import TagScriptEngine as tse
from starbot.core import commands

from ._tagscript import boosted, process_tagscript, unboosted
from .abc import CompositeMetaClass, MixinMeta


class EventMixin(MixinMeta, metaclass=CompositeMetaClass):
    SYSTEM_ENABLED: bool = False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return
        if message.guild.system_channel is None or (
            message.guild.system_channel
            and not message.guild.system_channel.permissions_for(message.guild.me).view_channel
        ):
            self.SYSTEM_ENABLED: bool = False
            return
        if message.guild.system_channel_flags.premium_subscriptions and message.type in (
            discord.MessageType.premium_guild_subscription,
            discord.MessageType.premium_guild_tier_1,
            discord.MessageType.premium_guild_tier_2,
            discord.MessageType.premium_guild_tier_3,
        ):
            self.SYSTEM_ENABLED: bool = True
            self.bot.dispatch("member_boost", message.author, "system")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if not after.guild:
            return
        if (
            after.guild.system_channel is None
            or not after.guild.system_channel_flags.premium_subscriptions
        ):
            return
        if role := after.guild.premium_subscriber_role:
            if role in before.roles and role not in after.roles:
                self.bot.dispatch("member_unboost", before, "premium_subscriber_role")
            elif role not in before.roles and role in after.roles:
                self.bot.dispatch("member_boost", after, "premium_subscriber_role")

    @commands.Cog.listener()
    async def on_member_boost(
        self, member: discord.Member, type: Literal["system", "premium_subscriber_role"]
    ) -> None:
        if self.SYSTEM_ENABLED and type.lower() == "premium_subscriber_role":
            return
        guild: discord.Guild = member.guild
        channels: List[int] = await self.config.guild(guild).boost_message.channels()
        message: str = await self.config.guild(guild).boost_message.boosted()
        toggle: bool = await self.config.guild(guild).boost_message.toggle()
        if not toggle:
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        kwargs: Dict[str, Any] = process_tagscript(
            message,
            {
                "member": tse.MemberAdapter(member),
                "guild": tse.GuildAdapter(guild),
            },
        )
        if not kwargs:
            await self.config.guild(member.guild).boost_message.boosted.clear()
            kwargs: Dict[str, Any] = process_tagscript(
                boosted,
                {
                    "member": tse.MemberAdapter(member),
                    "guild": tse.GuildAdapter(guild),
                },
            )
        for channel_id in channels:
            channel: discord.TextChannel = guild.get_channel(channel_id)
            if channel:
                if not channel.permissions_for(guild.me).send_messages:
                    return
                await channel.send(**kwargs)

    @commands.Cog.listener()
    async def on_member_unboost(
        self, member: discord.Member, type: Literal["premium_subscriber_role"]
    ) -> None:
        guild: discord.Guild = member.guild
        channels: List[int] = await self.config.guild(guild).boost_message.channels()
        message: str = await self.config.guild(guild).boost_message.unboosted()
        toggle: bool = await self.config.guild(guild).boost_message.toggle()
        if not toggle:
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        kwargs: Dict[str, Any] = process_tagscript(
            message,
            {
                "member": tse.MemberAdapter(member),
                "guild": tse.GuildAdapter(guild),
            },
        )
        if not kwargs:
            await self.config.guild(member.guild).boost_message.unboosted.clear()
            kwargs: Dict[str, Any] = process_tagscript(
                unboosted,
                {
                    "member": tse.MemberAdapter(member),
                    "guild": tse.GuildAdapter(guild),
                },
            )
        for channel_id in channels:
            channel: discord.TextChannel = guild.get_channel(channel_id)
            if channel:
                if not channel.permissions_for(guild.me).send_messages:
                    return
                await channel.send(**kwargs)
