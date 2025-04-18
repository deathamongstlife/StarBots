import calendar
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Union

import discord
from starbot.core import bank, commands, errors
from starbot.core.i18n import Translator
from starbot.core.utils.chat_formatting import humanize_number

from ..abc import MixinMeta

log = logging.getLogger("red.vrt.bankevents")
_ = Translator("BankEvents", __file__)


class PaydayClaimInformation(NamedTuple):
    member: discord.Member
    channel: Union[discord.TextChannel, discord.Thread, discord.ForumChannel]
    message: discord.Message
    amount: int
    old_balance: int
    new_balance: int

    def to_dict(self) -> dict:
        return {
            "member": self.member.id,
            "channel": self.channel.id,
            "message": self.message.id,
            "amount": self.amount,
            "old_balance": self.old_balance,
            "new_balance": self.new_balance,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class PaydayOverride(MixinMeta):
    @commands.command(hidden=True)
    @commands.guild_only()
    async def payday_override(self, ctx: commands.Context):
        cog = self.bot.get_cog("Economy")
        if cog is None:
            raise commands.ExtensionError("Economy cog is not loaded.")

        author = ctx.author
        guild = ctx.guild

        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())
        credits_name = await bank.get_currency_name(guild)
        old_balance = await bank.get_balance(author)
        if await bank.is_global():
            next_payday = await cog.config.user(author).next_payday() + await cog.config.PAYDAY_TIME()
            if cur_time >= next_payday:
                credit_amount = await cog.config.PAYDAY_CREDITS()
                try:
                    new_balance = await bank.deposit_credits(author, credit_amount)
                except errors.BalanceTooHigh as exc:
                    new_balance = await bank.set_balance(author, exc.max_balance)
                    await ctx.send(
                        _(
                            "You've reached the maximum amount of {currency}! "
                            "Please spend some more \N{GRIMACING FACE}\n\n"
                            "You currently have {new_balance} {currency}."
                        ).format(currency=credits_name, new_balance=humanize_number(exc.max_balance))
                    )
                    payload = PaydayClaimInformation(
                        author, ctx.channel, ctx.message, exc.max_balance - credit_amount, old_balance, new_balance
                    )
                    self.bot.dispatch("red_economy_payday_claim", payload)
                    return

                await cog.config.user(author).next_payday.set(cur_time)

                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{author.mention} Here, take some {currency}. "
                        "Enjoy! (+{amount} {currency}!)\n\n"
                        "You currently have {new_balance} {currency}.\n\n"
                        "You are currently #{pos} on the global leaderboard!"
                    ).format(
                        author=author,
                        currency=credits_name,
                        amount=humanize_number(credit_amount),
                        new_balance=humanize_number(await bank.get_balance(author)),
                        pos=humanize_number(pos) if pos else pos,
                    )
                )
                payload = PaydayClaimInformation(
                    author, ctx.channel, ctx.message, credit_amount, new_balance, old_balance
                )
                self.bot.dispatch("red_economy_payday_claim", payload)
            else:
                relative_time = discord.utils.format_dt(
                    datetime.now(timezone.utc) + timedelta(seconds=next_payday - cur_time), "R"
                )
                await ctx.send(
                    _("{author.mention} Too soon. Your next payday is {relative_time}.").format(
                        author=author, relative_time=relative_time
                    )
                )
        else:
            # Gets the users latest successfully payday and adds the guilds payday time
            next_payday = await cog.config.member(author).next_payday() + await cog.config.guild(guild).PAYDAY_TIME()
            if cur_time >= next_payday:
                credit_amount = await cog.config.guild(guild).PAYDAY_CREDITS()
                for role in author.roles:
                    role_credits = await cog.config.role(role).PAYDAY_CREDITS()  # Nice variable name
                    if role_credits > credit_amount:
                        credit_amount = role_credits
                try:
                    new_balance = await bank.deposit_credits(author, credit_amount)
                except errors.BalanceTooHigh as exc:
                    new_balance = await bank.set_balance(author, exc.max_balance)
                    await ctx.send(
                        _(
                            "You've reached the maximum amount of {currency}! "
                            "Please spend some more \N{GRIMACING FACE}\n\n"
                            "You currently have {new_balance} {currency}."
                        ).format(currency=credits_name, new_balance=humanize_number(exc.max_balance))
                    )
                    payload = PaydayClaimInformation(
                        author, ctx.channel, ctx.message, exc.max_balance - credit_amount, new_balance, old_balance
                    )
                    self.bot.dispatch("red_economy_payday_claim", payload)
                    return

                # Sets the latest payday time to the current time
                next_payday = cur_time

                await cog.config.member(author).next_payday.set(next_payday)
                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{author.mention} Here, take some {currency}. "
                        "Enjoy! (+{amount} {currency}!)\n\n"
                        "You currently have {new_balance} {currency}.\n\n"
                        "You are currently #{pos} on the global leaderboard!"
                    ).format(
                        author=author,
                        currency=credits_name,
                        amount=humanize_number(credit_amount),
                        new_balance=humanize_number(await bank.get_balance(author)),
                        pos=humanize_number(pos) if pos else pos,
                    )
                )
                payload = PaydayClaimInformation(
                    author, ctx.channel, ctx.message, credit_amount, new_balance, old_balance
                )
                self.bot.dispatch("red_economy_payday_claim", payload)
            else:
                relative_time = discord.utils.format_dt(
                    datetime.now(timezone.utc) + timedelta(seconds=next_payday - cur_time), "R"
                )
                await ctx.send(
                    _("{author.mention} Too soon. Your next payday is {relative_time}.").format(
                        author=author, relative_time=relative_time
                    )
                )
