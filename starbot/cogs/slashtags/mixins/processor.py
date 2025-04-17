"""
MIT License

Copyright (c) 2020-2023 phenom4n4n
Copyright (c) 2023-present i-am-zaidali

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
from copy import copy
from functools import partial
from typing import List, Optional, Union

import discord
import TagScriptEngine as tse
from starbot.core import commands
from discord.ext.commands.context import Typing, DeferTyping

from ..abc import MixinMeta
from ..blocks import HideBlock, ReactBlock
from ..errors import RequireCheckFailure
from ..models import InteractionWrapper
from ..objects import FakeMessage, SlashTag, ApplicationCommand
from ..utils import dev_check, TemporaryAttributes

PL = commands.PrivilegeLevel
RS = commands.Requires

log = logging.getLogger("red.phenom4n4n.slashtags.processor")


class Processor(MixinMeta):
    OPTION_ADAPTERS = {
        discord.AppCommandOptionType.string: tse.StringAdapter,
        discord.AppCommandOptionType.integer: tse.IntAdapter,
        discord.AppCommandOptionType.user: tse.MemberAdapter,
        discord.AppCommandOptionType.channel: tse.ChannelAdapter,
        discord.AppCommandOptionType.role: tse.SafeObjectAdapter,
        discord.AppCommandOptionType.number: tse.StringAdapter,
        discord.AppCommandOptionType.mentionable: tse.SafeObjectAdapter,
    }
    EMPTY_ADAPTER = tse.StringAdapter("")

    def __init__(self, bot):
        tse_blocks = [
            tse.MathBlock(),
            tse.RandomBlock(),
            tse.RangeBlock(),
            tse.AnyBlock(),
            tse.IfBlock(),
            tse.AllBlock(),
            tse.BreakBlock(),
            tse.StrfBlock(),
            tse.StopBlock(),
            tse.AssignmentBlock(),
            tse.FiftyFiftyBlock(),
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.URLEncodeBlock(),
            tse.CommandBlock(),
            tse.RedirectBlock(),
            tse.OverrideBlock(),
            tse.CooldownBlock(),
        ]
        slash_blocks = [HideBlock(), ReactBlock()]
        self.engine = tse.Interpreter(tse_blocks + slash_blocks)

        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()
        super().__init__(bot)

    def get_adapter(
        self,
        option_type: discord.AppCommandOptionType,
        default: tse.Adapter = tse.StringAdapter,
    ) -> tse.Adapter:
        return self.OPTION_ADAPTERS.get(option_type, default)

    async def handle_seed_variables(
        self, interaction: InteractionWrapper, seed_variables: dict
    ) -> dict:
        seed_variables = seed_variables.copy()
        for option in interaction.options:
            adapter = self.get_adapter(option["type"])
            try:
                seed_variables[option["name"]] = adapter(option["value"])
            except Exception as exc:
                log.exception(
                    "Failed to initialize adapter %r for option %r:",
                    adapter,
                    option,
                    exc_info=exc,
                )
                seed_variables[option["name"]] = tse.StringAdapter(option["value"])

        command: ApplicationCommand = self.get_command(interaction.command_id)
        for original_option in command.options:
            if original_option.name not in seed_variables:
                log.debug(
                    "optional option %s not found, using empty adapter", original_option
                )
                seed_variables[original_option._rename or original_option.name] = (
                    self.EMPTY_ADAPTER
                )

        guild = interaction.guild
        author = interaction.author
        channel = interaction.channel
        seed_variables["author"] = tse.MemberAdapter(author)
        seed_variables["channel"] = tse.ChannelAdapter(channel)
        if guild:
            seed_variables["server"] = tse.GuildAdapter(guild)
            seed_variables["guild"] = tse.GuildAdapter(guild)

        command_type = interaction.command_type
        if command_type == discord.AppCommandType.user:
            target_id: int = interaction.target_id
            user = interaction.resolved.users[target_id]
            seed_variables["user"] = tse.MemberAdapter(user)
            seed_variables["target_id"] = tse.StringAdapter(target_id)
        elif command_type == discord.AppCommandType.message:
            target_id: int = interaction.target_id
            message = interaction.resolved.messages[target_id]
            seed_variables["message"] = tse.SafeObjectAdapter(message)
            seed_variables["target_id"] = tse.StringAdapter(target_id)
        return seed_variables

    async def process_tag(
        self,
        interaction: InteractionWrapper,
        tag: SlashTag,
        *,
        seed_variables: dict = None,
        **kwargs,
    ) -> str:
        log.debug("processing tag %s | options: %r", tag, interaction.options)
        seed_variables = await self.handle_seed_variables(
            interaction, seed_variables or {}
        )
        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        await tag.update_config()
        content = output.body[:2000] if output.body else None
        actions = output.actions

        embed = actions.get("embed", discord.utils.MISSING)
        ephemeral = actions.get("hide", False)

        try:
            await self.handle_requires(interaction, actions)
        except RequireCheckFailure:
            return

        if content or embed:
            message = await self.send_tag_response(
                interaction, actions, content, ephemeral=ephemeral, embed=embed
            )
            if message and (react := actions.get("react")):
                self.create_task(self.react_to_list(interaction.ctx, message, react))
        else:
            try:
                await interaction.interaction.response.defer(
                    ephemeral=ephemeral, thinking=True
                )
            except discord.NotFound:
                interaction.interaction.response._response_type = (
                    discord.InteractionResponseType.deferred_message_update
                )

        await self.process_commands(interaction, actions)

        if not interaction.completed:
            try:
                await interaction.send("Slash Tag completed.", ephemeral=True)
            except discord.NotFound:
                pass

    async def react_to_list(
        self, ctx: commands.Context, message: discord.Message, args: List[str]
    ):
        if not (message and args):
            return
        for arg in args:
            try:
                arg = await self.emoji_converter.convert(ctx, arg)
            except commands.BadArgument:
                pass
            try:
                await message.add_reaction(arg)
            except discord.HTTPException:
                pass

    async def handle_requires(self, interaction: InteractionWrapper, actions: dict):
        try:
            await self.validate_checks(interaction, actions)
        except RequireCheckFailure as error:
            response = error.response
            if response is not None and (response := response.strip()):
                await interaction.send(response[:2000], ephemeral=True)
            else:
                await interaction.send(
                    "You aren't allowed to use this tag.", ephemeral=True
                )
            raise

    async def process_commands(self, interaction: InteractionWrapper, actions: dict):
        commands = actions.get("commands")
        if not commands:
            return
        overrides = actions.get("overrides")
        command_tasks = []
        prefix = (await self.bot.get_valid_prefixes(interaction.guild))[0]
        for command in commands:
            inter = interaction.interaction
            message = await FakeMessage.from_interaction(inter, prefix + command)
            command_task = self.create_task(
                self.process_command(interaction, message, overrides)
            )
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    @staticmethod
    async def _send(
        self: commands.Context,
        org_send,
        wrapper: InteractionWrapper,
        content: str = None,
        **kwargs,
    ):
        # monkeypatching the ctx.send method so that I can store the returned message in the InteractionWrapper class
        # which would help me in knowing whether the interaction has been completed or not
        with TemporaryAttributes(self, interaction=wrapper.interaction):
            sent = await org_send(content=content, **kwargs)
            wrapper.responded = sent
            return sent

    @staticmethod
    def _typing(self: commands.Context, wrapper: InteractionWrapper, ephemeral=False):
        with TemporaryAttributes(self, interaction=wrapper.interaction):
            if self.interaction is None or self.interaction.response.is_done():
                return Typing(self)
            return DeferTyping(self, ephemeral=ephemeral)

    async def process_command(
        self,
        wrapper: InteractionWrapper,
        message: FakeMessage,
        overrides: dict,
    ):
        ctx: commands.Context = await self.bot.get_context(message)
        ctx.typing = partial(self._typing, ctx, wrapper)
        ctx.send = partial(self._send, ctx, ctx.send, wrapper)
        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
                # command = ctx.command.copy() # does not work as it makes ctx a regular argument
                requires: RS = copy(command.requires)
                priv_level = requires.privilege_level
                if priv_level not in (
                    PL.NONE,
                    PL.BOT_OWNER,
                    PL.GUILD_OWNER,
                ):
                    if overrides["admin"] and priv_level is PL.ADMIN:
                        requires.privilege_level = PL.NONE
                    elif overrides["mod"] and priv_level is PL.MOD:
                        requires.privilege_level = PL.NONE
                if overrides["permissions"] and requires.user_perms:
                    requires.user_perms = discord.Permissions.none()
                command.requires = requires
                ctx.command = command
            await self.bot.invoke(ctx)

    async def send_tag_response(
        self,
        interaction: InteractionWrapper,
        actions: dict,
        content: str = None,
        *,
        embed: discord.Embed = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        destination = interaction

        if target := actions.get("target"):
            if target == "dm":
                destination = interaction.author
                del kwargs["ephemeral"]
            elif target != "reply":
                try:
                    chan = await self.channel_converter.convert(interaction, target)
                except commands.BadArgument:
                    pass
                else:
                    if chan.permissions_for(interaction.ctx.me).send_messages:
                        destination = chan
                        del kwargs["ephemeral"]

        if not (content or embed is not None):
            return

        try:
            log.debug("sending to destination %r", destination)
            return await destination.send(content, embed=embed, **kwargs)
        except discord.HTTPException as exc:
            log.exception(
                "Error sending to destination:%r for interaction:%r\nkwargs:%r",
                destination,
                interaction,
                kwargs,
                exc_info=exc,
            )

    async def validate_checks(self, ctx: commands.Context, actions: dict):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [
            obj
            for obj in objects
            if isinstance(obj, (discord.Role, discord.TextChannel))
        ]
        return objects[0] if objects else None

    async def validate_requires(self, ctx: commands.Context, requires: dict):
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    return
            elif role_or_channel == ctx.channel:
                return
        raise RequireCheckFailure(requires["response"])

    @staticmethod
    def blacklist_check(
        ctx: commands.Context,
        role_or_channel: Union[discord.Role, discord.TextChannel],
        roles: List[discord.Role],
    ) -> bool:
        if isinstance(role_or_channel, discord.Role):
            return role_or_channel in roles
        return role_or_channel == ctx.channel

    async def validate_blacklist(self, ctx: commands.Context, blacklist: dict):
        roles: List[discord.Role] = ctx.author.roles
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if self.blacklist_check(ctx, role_or_channel, roles):
                raise RequireCheckFailure(blacklist["response"])

    async def slash_eval(self, interaction: InteractionWrapper):
        if not await self.bot.is_owner(interaction.author):
            return await interaction.send("Only bot owners may eval.", ephemeral=True)
        await interaction.response.defer()
        ctx = interaction.ctx
        dev = dev_check(self)
        await dev._eval(ctx, body=interaction.options[0]["value"])
