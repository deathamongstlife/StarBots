import re
from typing import Pattern, Union
from Star-Utils import Cog, CogsUtils

import discord
from discord.ext.commands.converter import IDConverter
from discord.ext.commands.errors import BadArgument
from red_commons.logging import getLogger
from starbot.core import Config, VersionInfo, commands, version_info
from starbot.core.i18n import Translator
from starbot.core.utils.chat_formatting import humanize_list, pagify

log = getLogger("red.trusty-cogs.inviteblocklist")

_ = Translator("ExtendedModLog", __file__)

INVITE_RE: Pattern = re.compile(
    r"(?:https?\:\/\/)?discord(?:\.gg|(?:app)?\.com\/invite)\/(.+)", re.I
)
# https://github.com/Rapptz/discord.py/blob/master/discord/utils.py#L448


class ChannelUserRole(IDConverter):
    """
    This will check to see if the provided argument is a channel, user, or role

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/StarBot/blob/V3/develop/starbot/cogs/mod/mod.py#L24
    """

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Union[discord.TextChannel, discord.Member, discord.Role]:
        guild = ctx.guild
        result = None
        id_match = self._get_id_match(argument)
        channel_match = re.match(r"<#([0-9]+)>$", argument)
        member_match = re.match(r"<@!?([0-9]+)>$", argument)
        role_match = re.match(r"<@&([0-9]+)>$", argument)
        for converter in ["channel", "role", "member"]:
            if converter == "channel":
                match = id_match or channel_match
                if match:
                    channel_id = match.group(1)
                    result = guild.get_channel(int(channel_id))
                else:
                    result = discord.utils.get(guild.text_channels, name=argument)
            if converter == "member":
                match = id_match or member_match
                if match:
                    member_id = match.group(1)
                    result = guild.get_member(int(member_id))
                else:
                    result = guild.get_member_named(argument)
            if converter == "role":
                match = id_match or role_match
                if match:
                    role_id = match.group(1)
                    result = guild.get_role(int(role_id))
                else:
                    result = discord.utils.get(guild._roles.values(), name=argument)
            if result:
                break
        if not result:
            msg = ("{arg} is not a valid channel, user or role.").format(arg=argument)
            raise BadArgument(msg)
        return result


class InviteBlocklist(Cog):
        
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=218773382617890828)
        self.config.register_guild(
            blacklist=[],
            whitelist=[],
            all_invites=False,
            immunity_list=[],
        )
        self.config.register_guild(
            added_by={}
        )

    async def red_delete_data_for_user(self, **kwargs):
        """
        Nothing to delete
        """
        return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        await self._handle_message_search(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """
        Handle messages edited with links
        """
        if not payload.guild_id:
            return
        if payload.cached_message:
            guild = payload.cached_message.guild
        else:
            guild = self.bot.get_guild(int(payload.guild_id))
        if guild is None:
            return
        chan = guild.get_channel(payload.channel_id)
        if chan is None:
            return
        if version_info >= VersionInfo.from_str("3.4.0"):
            if await self.bot.cog_disabled_in_guild(self, guild):
                return
        guild_settings = await self.config.guild(guild).all()
        if (
            guild_settings["blacklist"]
            or guild_settings["whitelist"]
            or guild_settings["all_invites"]
        ):
            if payload.cached_message is not None:
                await self._handle_message_search(payload.cached_message)
            else:
                if "edited_timestamp" not in payload.data:
                    # This should only be happening on links posted by users
                    return
                msg = discord.Message(state=chan._state, channel=chan, data=payload.data)
                # construct the message object regardless of cache state
                # d.py will normally ignore these edits and not build the full object
                # so we manually construct it here for simplicity
                await self._handle_message_search(msg)

    async def check_immunity_list(self, message: discord.Message) -> bool:
        is_immune = False
        if not message.guild:
            return True
        if await self.bot.is_owner(message.author):
            return True
        global_perms = await self.bot.allowed_by_whitelist_blacklist(message.author)
        if not global_perms:
            return global_perms
        immunity_list = await self.config.guild(message.guild).immunity_list()
        channel = message.channel
        if immunity_list:
            if channel.id in immunity_list:
                is_immune = True
            if channel.category_id and channel.category_id in immunity_list:
                is_immune = True
            if message.author.id in immunity_list:
                is_immune = True
            for role in getattr(message.author, "roles", []):
                if role.is_default():
                    continue
                if role.id in immunity_list:
                    is_immune = True
        return is_immune

    async def _handle_message_search(self, message: discord.Message):
        if await self.bot.is_automod_immune(message.author):
            return
        if version_info >= VersionInfo.from_str("3.4.0"):
            if await self.bot.cog_disabled_in_guild(self, message.guild):
                return
        if await self.check_immunity_list(message) is True:
            log.debug("Message context is immune from invite blocklist")
            return
        find = INVITE_RE.findall(message.clean_content)
        guild = message.guild
        if find and await self.config.guild(message.guild).all_invites():
            try:
                await message.delete()
            except discord.errors.Forbidden:
                log.error(
                    "I tried to delete an invite link posted in %s "
                    "but lacked the permission to do so",
                    guild.name,
                )
            return
        if whitelist := await self.config.guild(message.guild).whitelist():
            for i in find:
                invite = await self.bot.fetch_invite(i)
                if invite.guild.id == message.guild.id:
                    continue
                if invite.guild.id not in whitelist:
                    try:
                        await message.delete()
                    except discord.errors.Forbidden:
                        log.error(
                            "I tried to delete an invite link posted in %s "
                            "but lacked the permission to do so",
                            guild.name,
                        )
                    return
            return
        if blacklist := await self.config.guild(message.guild).blacklist():
            for i in find:
                invite = await self.bot.fetch_invite(i)
                if invite.guild.id == message.guild.id:
                    continue
                if invite.guild.id in blacklist:
                    try:
                        await message.delete()
                    except discord.errors.Forbidden:
                        log.error(
                            "I tried to delete an invite link posted in %s "
                            "but lacked the permission to do so",
                            guild.name,
                        )
                    return
            return

    @commands.group(name="inviteblock", aliases=["ibl", "inviteblocklist"])
    @commands.mod_or_permissions(manage_messages=True)
    async def invite_block(self, ctx: commands.Context):
        """
        Settings for managing invite link blocking
        """
        pass

    @invite_block.group(name="blocklist", aliases=["blacklist", "bl", "block"])
    async def invite_blocklist(self, ctx: commands.Context):
        """
        Commands for setting the blocklist
        """
        pass

    @invite_block.group(name="allowlist", aliases=["whitelist", "wl", "al", "allow"])
    async def invite_allowlist(self, ctx: commands.Context):
        """
        Commands for setting the blocklist
        """
        pass

    @invite_block.group(name="immunity", aliases=["immune"])
    async def invite_immunity(self, ctx: commands.Context):
        """
        Commands for fine tuning allowed channels, users, or roles
        """
        pass

    ##########################################################################################
    #                                    Blocklist Settings                                  #
    ##########################################################################################

    @invite_block.command()
    @commands.mod_or_permissions(manage_messages=True)
    async def blockall(self, ctx: commands.Context, set_to: bool):
        """
        Automatically remove all invites regardless of their destination
        """
        await self.config.guild(ctx.guild).all_invites.set(set_to)
        if set_to:
            await ctx.send(_("Okay, I will delete all invite links posted."))
        else:
            await ctx.send(
                _(
                    "Okay I will only delete invites if the server "
                    "destination is in my blocklist or allowlist."
                )
            )

    @invite_blocklist.command(name="add")
    async def add_to_blocklist(
        self,
        ctx: commands.Context,
        *invite_or_guild_id: Union[discord.Invite, discord.Guild, int],
    ):
        """
        Add a guild ID to the blocklist, providing an invite link will also work

        `[invite_or_guild_id]` The guild ID or invite to the guild you want to have
        invite links blocked from.
        """
        guilds_blocked = []
        added_by = await self.config.guild(ctx.guild).added_by()
        async with self.config.guild(ctx.guild).blacklist() as blacklist:
            for i in invite_or_guild_id:
                if isinstance(i, int):
                    if i not in blacklist:
                        blacklist.append(i)
                        guilds_blocked.append(str(i))
                        added_by[str(i)] = ctx.author.id
                elif isinstance(i, discord.Invite):
                    if i.guild and i.guild.id not in blacklist:
                        guilds_blocked.append(f"{i.guild.name} - {i.guild.id}")
                        blacklist.append(i.guild.id)
                        added_by[str(i.guild.id)] = ctx.author.id
                elif isinstance(i, discord.Guild):
                    if i.id not in blacklist:
                        guilds_blocked.append(f"{i.name} - {i.id}")
                        blacklist.append(i.id)
                        added_by[str(i.id)] = ctx.author.id
        await self.config.guild(ctx.guild).added_by.set(added_by)
        if guilds_blocked:
            await ctx.send(
                _("Now blocking invites from {guild}.").format(guild=humanize_list(guilds_blocked))
            )
        else:
            await ctx.send(_("None of the provided invite links or guild ID's are new."))

    @invite_blocklist.command(name="remove", aliases=["del", "rem"])
    async def remove_from_blocklist(
        self,
        ctx: commands.Context,
        *thing_to_block: Union[discord.Invite, discord.Guild, int],
    ):
        """
        Add a guild ID to the blocklist, providing an invite link will also work

        `[invite_or_guild_id]` The guild ID or invite to the guild you not longer want to have
        invite links blocked from.
        """
        guilds_blocked = []
        added_by = await self.config.guild(ctx.guild).added_by()
        async with self.config.guild(ctx.guild).blacklist() as blacklist:
            for i in thing_to_block:
                if isinstance(i, int):
                    if i in blacklist:
                        blacklist.remove(i)
                        guilds_blocked.append(str(i))
                        added_by.pop(str(i), None)
                elif isinstance(i, discord.Invite):
                    if i.guild and i.guild.id in blacklist:
                        guilds_blocked.append(f"{i.guild.name} - {i.guild.id}")
                        blacklist.remove(i.guild.id)
                        added_by.pop(str(i.guild.id), None)
                elif isinstance(i, discord.Guild):
                    if i.id in blacklist:
                        guilds_blocked.append(f"{i.name} - {i.id}")
                        blacklist.remove(i.id)
                        added_by.pop(str(i.id), None)
        await self.config.guild(ctx.guild).added_by.set(added_by)
        if guilds_blocked:
            await ctx.send(
                _("Removed {guild} from blocklist.").format(guild=humanize_list(guilds_blocked))
            )
        else:
            await ctx.send(_("None of the provided invite links or guild ID's are being blocked."))

    @invite_blocklist.command(name="info")
    async def blocklist_info(self, ctx: commands.Context):
        """
        Show what guild ID's are in the invite link blocklist
        """
        blacklist = await self.config.guild(ctx.guild).blacklist()
        added_by = await self.config.guild(ctx.guild).added_by()
        msg = _("__Guild ID's Blocked__:\n{guilds}").format(
            guilds="\n".join(str(g) for g in blacklist)
        )
        block_list = await self.config.guild(ctx.guild).channel_user_role_allow()
        if block_list:
            msg += _("__Blocked Channels, Users, and Roles:__\n{chan_user_roel}").format(
                chan_user_role="\n".join(
                    await ChannelUserRole().convert(ctx, str(obj_id)) for obj_id in block_list
                )
            )
        for page in pagify(msg):
            await ctx.maybe_send_embed(page)

    @invite_blocklist.command(name="list")
    async def added_by_info(self, ctx: commands.Context):
        """
        Show which servers were added to the blocklist and who added them
        """
        added_by = await self.config.guild(ctx.guild).added_by()
        if not added_by:
            await ctx.send("No servers have been added to the blocklist.")
            return

        embed = discord.Embed(title="Blocked Servers", color=discord.Color.blue())
        for guild_id, user_id in added_by.items():
            guild = self.bot.get_guild(int(guild_id))
            guild_name = guild.name if guild else "Unknown"
            user = self.bot.get_user(user_id)
            user_name = user.name if user else "Unknown"
            embed.add_field(name=f"Server: {guild_name} ({guild_id})", value=f"Added by: {user_name}", inline=False)

        await ctx.send(embed=embed)

    ##########################################################################################
    #                                    Alowlist Settings                                   #
    ##########################################################################################

    @invite_allowlist.command(name="add")
    async def add_to_allowlist(
        self,
        ctx: commands.Context,
        *invite_or_guild_id: Union[discord.Invite, discord.Guild, int],
    ):
        """
        Add a guild ID to the allowlist, providing an invite link will also work

        `[invite_or_guild_id]` The guild ID or invite to the guild you want to have
        invites allowed from.
        """
        guilds_blocked = []
        async with self.config.guild(ctx.guild).whitelist() as whitelist:
            for i in invite_or_guild_id:
                if isinstance(i, int):
                    if i not in whitelist:
                        whitelist.append(i)
                        guilds_blocked.append(str(i))
                elif isinstance(i, discord.Invite):
                    if i.guild and i.guild.id not in whitelist:
                        guilds_blocked.append(f"{i.guild.name} - {i.guild.id}")
                        whitelist.append(i.guild.id)
                elif isinstance(i, discord.Guild):
                    if i.id not in whitelist:
                        guilds_blocked.append(f"{i.name} - {i.id}")
                        whitelist.append(i.id)
        if guilds_blocked:
            await ctx.send(
                _("Now Allowing invites from {guild}.").format(guild=humanize_list(guilds_blocked))
            )
        else:
            await ctx.send(_("None of the provided invite links or ID's are new."))

    @invite_allowlist.command(name="remove", aliases=["del", "rem"])
    async def remove_from_allowlist(
        self, ctx: commands.Context, *invite_or_guild_id: Union[discord.Invite, discord.Guild, int]
    ):
        """
        Add a guild ID to the allowlist, providing an invite link will also work

        `[invite_or_guild_id]` The guild ID or invite to the guild you not longer want to have
        invites allowed from.
        """
        guilds_blocked = []
        async with self.config.guild(ctx.guild).whitelist() as whitelist:
            for i in invite_or_guild_id:
                if isinstance(i, int):
                    if i in whitelist:
                        whitelist.remove(i)
                        guilds_blocked.append(str(i))
                elif isinstance(i, discord.Invite):
                    if i.guild and i.guild.id in whitelist:
                        guilds_blocked.append(f"{i.guild.name} - {i.guild.id}")
                        whitelist.remove(i.guild.id)
                elif isinstance(i, discord.Guild):
                    if i.id in whitelist:
                        guilds_blocked.append(f"{i.name} - {i.id}")
                        whitelist.remove(i.id)
        if guilds_blocked:
            await ctx.send(
                _("Removed {guild} from allowlist.").format(guild=humanize_list(guilds_blocked))
            )
        else:
            await ctx.send(
                _("None of the provided invite links or guild ID's are currently allowed.")
            )

    @invite_allowlist.command(name="info")
    async def allowlist_info(self, ctx: commands.Context):
        """
        Show what guild ID's are in the invite link allowlist
        """
        whitelist = await self.config.guild(ctx.guild).whitelist()
        msg = _("__Guild ID's Allowed__:\n{guilds}").format(
            guilds="\n".join(str(g) for g in whitelist)
        )
        allow_list = await self.config.guild(ctx.guild).channel_user_role_allow()
        if allow_list:
            msg += _("__Allowed Channels, Users, and Roles:__\n{chan_user_roel}").format(
                chan_user_role="\n".join(
                    await ChannelUserRole().convert(ctx, str(obj_id)) for obj_id in allow_list
                )
            )
        for page in pagify(msg):
            await ctx.maybe_send_embed(page)

    ##########################################################################################
    #                                  Immunity Settings                                     #
    ##########################################################################################

    @invite_immunity.command(name="add")
    async def add_to_invite_immunity(
        self, ctx: commands.Context, *channel_user_role: ChannelUserRole
    ):
        """
        Add a guild ID to the allowlist, providing an invite link will also work

        `[channel_user_role...]` is the channel, user or role to whitelist
        (You can supply more than one of any at a time)
        """
        if len(channel_user_role) < 1:
            return await ctx.send(
                _("You must supply 1 or more channels users or roles to be allowed.")
            )
        async with self.config.guild(ctx.guild).immunity_list() as whitelist:
            for obj in channel_user_role:
                if obj.id not in whitelist:
                    whitelist.append(obj.id)
        msg = _("`{list_type}` added to the whitelist.")
        list_type = humanize_list([c.name for c in channel_user_role])
        await ctx.send(msg.format(list_type=list_type))

    @invite_immunity.command(name="remove", aliases=["del", "rem"])
    async def remove_from_invite_immunity(
        self, ctx: commands.Context, *channel_user_role: ChannelUserRole
    ):
        """
        Add a guild ID to the allowlist, providing an invite link will also work

        `[channel_user_role...]` is the channel, user or role to remove from the whitelist
        (You can supply more than one of any at a time)
        """
        if len(channel_user_role) < 1:
            return await ctx.send(
                _("You must supply 1 or more channels users or roles to be whitelisted.")
            )
        async with self.config.guild(ctx.guild).immunity_list() as whitelist:
            for obj in channel_user_role:
                if obj.id in whitelist:
                    whitelist.remove(obj.id)
        msg = _("`{list_type}` removed from the whitelist.")
        list_type = humanize_list([c.name for c in channel_user_role])
        await ctx.send(msg.format(list_type=list_type))

    @invite_immunity.command(name="info")
    async def allowlist_context_info(self, ctx: commands.Context):
        """
        Show what channels, users, and roles are in the invite link allowlist
        """
        msg = _("Invite immunity list for {guild}:\n").format(guild=ctx.guild.name)
        whitelist = await self.config.guild(ctx.guild).immunity_list()
        can_embed = ctx.channel.permissions_for(ctx.me).embed_links
        for obj_id in whitelist:
            obj = await ChannelUserRole().convert(ctx, str(obj_id))
            if isinstance(obj, discord.TextChannel):
                msg += f"{obj.mention}\n"
                continue
            if can_embed:
                msg += f"{obj.mention}\n"
                continue
            else:
                msg += f"{obj.name}\n"
        for page in pagify(msg):
            await ctx.maybe_send_embed(page)
