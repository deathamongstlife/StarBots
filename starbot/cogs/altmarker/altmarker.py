from dataclasses import dataclass
import logging
from typing import List, Optional
from Star-Utils import Cog, CogsUtils

import discord
from starbot.core import Config, commands
from starbot.core.modlog import Case
from starbot.core.i18n import Translator, cog_i18n
from starbot.core.utils.chat_formatting import box

from .exceptions import AltAlreadyRegistered, AltNotRegistered

_ = Translator("AltMarker", __file__)


@dataclass
class Alt:
    id: int
    name: str

    @classmethod
    def from_dict(cls, data):
        a = cls(None, None)
        a.__dict__.update(data)
        return a


@cog_i18n(_)
class AltMarker(Cog):
    """
    Mark alt accounts
    """

    

    async def red_delete_data_for_user(self, *, user_id, requester):
        pass  # TODO data deletion

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=232329032022)
        self.config.register_member(alts=[])
        self.config.register_guild(notify=None)
        self.log = logging.getLogger("red.cog.dav-cogs.altmarker")

    @commands.commands.Cog.listener()
    async def on_modlog_case_create(self, case: Case):
        member = (
            case.guild.get_member(case.user)
            if type(case.user) is int
            else case.guild.get_member(case.user.id)
        )
        alts = await self.get_alts(member)
        if alts:
            channel_id = await self.config.guild(case.guild).notify()
            if channel_id:
                channel = case.guild.get_channel(channel_id)
                if channel:
                    await channel.send(
                        _(
                            "There are registered alt accounts for this member:\n{alt_message}"
                        ).format(alt_message=await self._get_alts_string(member, alts))
                    )
                    if case.channel:
                        case_channel = (
                            case.guild.get_channel(case.channel)
                            if type(case.channel) is int
                            else case.guild.get_channel(case.channel.id)
                        )
                        await case_channel.send(
                            _(
                                "There are registered alt accounts for this member.\nPlease check {notify_channel} for more information."
                            ).format(notify_channel=channel.mention)
                        )
                else:
                    await self.config.guild(case.guild).notify.clear()
                    self.log.warning(
                        f"Notification channel for {case.guild} not found. Resetting guild config."
                    )

    @commands.commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if channel_id := await self.config.guild(member.guild).notify():
            alts = await self.get_alts(member)
            if alts:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    await channel.send(
                        _("A member with known alts joined the guild:\n{alt_message}").format(
                            alt_message=await self._get_alts_string(member, alts)
                        )
                    )
                else:
                    self.log.warning(f"Notification channel for {member.guild} not found.")

    @commands.commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if channel_id := await self.config.guild(member.guild).notify():
            alts = await self.get_alts(member)
            if alts:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    await channel.send(
                        _("A member with known alts left the guild:\n{alt_message}").format(
                            alt_message=await self._get_alts_string(member, alts)
                        )
                    )
                else:
                    self.log.warning(f"Notification channel for {member.guild} not found.")

    @commands.group(aliases=["alts"])
    async def alt(self, ctx: commands.Context):
        """Mark or unmark an alt acount"""

    @alt.command(aliases=["add"])
    async def mark(self, ctx: commands.Context, member: discord.Member, alt: discord.Member):
        """Mark an alt account"""
        try:
            await self.add_alt(member, alt)
            await ctx.send(
                _("{alt} is now marked as an alt of {user}.").format(alt=alt, user=member)
            )
        except AltAlreadyRegistered as error:
            await ctx.send(error.message)
        finally:
            await ctx.send(await self._get_alts_string(member))

    @commands.mod()
    @alt.command()
    async def get(self, ctx: commands.Context, member: discord.Member):
        """Get alts of a member"""
        await ctx.send(await self._get_alts_string(member))

    @commands.mod()
    @alt.command(aliases=["remove", "delete"])
    async def unmark(self, ctx: commands.Context, member: discord.Member, alt: discord.Member):
        """Unmark an alt account"""
        try:
            await self.remove_alt(member, alt)
            await ctx.send(
                _("{alt} is no longer marked as an alt of {user}.").format(alt=alt, user=member)
            )
        except AltNotRegistered as error:
            await ctx.send(error.message)
        finally:
            await ctx.send(await self._get_alts_string(member))

    @commands.admin()
    @commands.group()
    async def amset(self, ctx: commands.Context):
        """Set altmarker settings"""

    @amset.command()
    async def notify(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Toggle notification on moderation actions"""
        if channel is None:
            await ctx.send(_("Notifications are now disabled."))
        else:
            await self.config.guild(ctx.guild).notify.set(channel.id)
            await ctx.send(
                _("Notifications will be sent to {notify}").format(notify=channel.mention)
            )

    async def add_alt(self, member: discord.Member, alt: discord.Member) -> None:
        """
        Add an alt to a member

        Parameters
        ----------
        member: discord.Member
            The member to add an alt to
        alt: discord.Member
            The alt to add

        Raises
        ------
        AltAlreadyRegistered
            If the alt is already registered to the specified member
        """
        if not await self.is_alt(member, alt):
            alts = await self.get_alts(member) + await self.get_alts(alt)
            alts.append(Alt(alt.id, str(alt)))
            alts.append(Alt(member.id, str(member)))
            await self._save_alt_list(member.guild, alts)
        else:
            raise AltAlreadyRegistered(
                _("{alt} is already an alt of {member}.").format(alt=alt, member=member),
                member=member,
                alt=alt,
            )

    async def remove_alt(self, member: discord.Member, alt: discord.Member) -> None:
        """
        Remove an alt from a member

        Parameters
        ----------
        member : discord.Member
            The member to remove the alt from
        alt : discord.Member
            The alt to remove

        Raises
        ------
        AltNotRegistered
            If the member provided in alt is not registered as an alt of the member
        """
        if await self.is_alt(member, alt):
            alts = await self.get_alts(member)
            await self.config.member(alt).clear()
            alts = [a for a in alts if a.id != alt.id]  # Delete alt from list
            alts.append(
                Alt(member.id, str(member))
            )  # Make sure config entry for member gets updated
            await self._save_alt_list(member.guild, alts)
        else:
            raise AltNotRegistered(
                _("{alt} is not an alt of {member}.").format(alt=alt, member=member),
                member=member,
                alt=alt,
            )

    async def get_alts(self, member: discord.Member) -> List[Alt]:
        """
        Get alts of a member

        Parameters
        ----------
        member: discord.Member
            The member to get alts for

        Returns
        -------
        List[Alt]
            List of alts. This list may be empty.
        """
        return [Alt.from_dict(a) for a in await self.config.member(member).alts()]

    async def is_alt(self, member: discord.Member, alt: discord.Member) -> bool:
        """
        Determine if a member is a known alt of another member

        Parameters
        ----------
        member: discord.Member
            The member to check
        alt: discord.Member
            The alt to check

        Returns
        -------
        bool
            True if the alt is registered as an alt of the member, False otherwise
        """
        alts = await self.get_alts(member)
        for a in alts:
            if a.id == alt.id:
                return True
        return False

    async def _get_alts_string(
        self, member: discord.Member, alts: Optional[List[Alt]] = None
    ) -> str:
        if not alts:
            alts = await self.get_alts(member)
        return _("Known accounts of {member}: {alts}").format(
            member=member,
            alts=box(
                "\n - " + "\n - ".join([f"{a.name}({a.id})" for a in alts]),
                lang="md",
            ),
        )

    async def _save_alt_list(self, guild: discord.Guild, alts: List[Alt]):
        for alt_account in alts:
            altcopy = alts.copy()
            altcopy.remove(alt_account)
            altcopy = [a.__dict__ for a in altcopy]
            await self.config.member_from_ids(guild.id, alt_account.id).alts.set(altcopy)
