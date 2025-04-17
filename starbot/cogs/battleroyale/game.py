"""
MIT License

Copyright (c) 2023-present japandotorg

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
from Star-Utils import Cog
import asyncio
import random
import time
from collections import Counter
from typing import TYPE_CHECKING, Any, Coroutine, List, Optional, Protocol, TypeVar

import discord
from starbot.core import bank, commands
from starbot.core.errors import BalanceTooHigh
from starbot.core.utils.chat_formatting import humanize_list, pagify

from .constants import EMOJIS, PROMPTS, WINNER_PROMPTS
from .utils import exceptions
from .views import RemainingPlayerView

if TYPE_CHECKING:
    from .core import BattleRoyale


T = TypeVar("T", covariant=True)

EDIT_ORIGINAL_MESSAGE = False


__all__ = ("Game",)


class GameBase(Protocol[T]):
    def __init__(self, cog: Cog, delay: int = 10, skip: bool = False) -> None: ...

    async def start(
        self,
        ctx: commands.Context,
        players: List[discord.Member],
        original_message: Optional[discord.Message] = None,
    ) -> discord.Member: ...


class Game(GameBase):
    def __init__(self, cog: "BattleRoyale", delay: int = 10, skip: bool = False) -> None:
        self.cog: "BattleRoyale" = cog
        self.ctx: commands.Context = None  # type: ignore

        self.delay: int = delay
        self.skip: bool = skip

        self.players: List[discord.Member] = []
        self.messages: List[discord.Message] = []
        self.original_message: discord.Message = None  # type: ignore

    @exceptions
    async def start(
        self,
        ctx: commands.Context,
        players: List[discord.Member],
        original_message: Optional[discord.Message] = None,
    ) -> discord.Member:
        self.ctx: commands.Context = ctx
        self.players: List[discord.Member] = players
        self.remaining_players: List[discord.Member] = self.players.copy()
        self.messages: List[discord.Message] = []
        if original_message is not None:
            self.messages.append(original_message)
            self.original_message: discord.Message = original_message
        else:
            embed: discord.Embed = discord.Embed(
                title="BattleRoyale", color=await self.ctx.embed_color()
            )
            remaining_players_str = humanize_list(
                [
                    m.global_name if m.global_name else m.display_name
                    for m in sorted(
                        self.remaining_players,
                        key=lambda m: m.global_name if m.global_name else m.display_name,
                    )
                ]
            )
            remaining_players_str = (
                f"{remaining_players_str[:3000]}..."
                if len(remaining_players_str) > 3000
                else remaining_players_str
            )
            embed.description = (
                f"**{len(self.remaining_players)} Remaining Players:**\n{remaining_players_str}."
            )
            self.messages.append(original_message)
            self.original_message: discord.Message = await self.ctx.send(embed=embed)
        await self.cog.add_stats_to_leaderboard("games", users=self.players)
        places: List[discord.Member] = []
        kills: Counter = Counter()
        prompts = ""
        i = 0
        async with ctx.typing():
            while len(self.remaining_players) > 1:
                killed = random.choice(self.remaining_players)
                self.remaining_players.remove(killed)
                killer = random.choice(self.remaining_players)
                kills[killer] += 1
                places.insert(0, killed)
                await self.cog.add_stats_to_leaderboard("kills", users=[killer])
                await self.cog.add_stats_to_leaderboard("deaths", users=[killed])
                if not self.skip:
                    custom_emoji: Optional[discord.Emoji] = self.ctx.bot.get_emoji(
                        1049726529908777002
                    )
                    emoji: discord.PartialEmoji = random.choice(EMOJIS)
                    prompts += "\n" + random.choice(PROMPTS).format(
                        emoji=custom_emoji if custom_emoji else emoji,
                        killer=f"**{killer.global_name if killer.global_name else killer.display_name}**",
                        killed=f"**{killed.global_name if killed.global_name else killed.display_name}**",
                    )
                    if len(self.players) <= 30 or len(self.remaining_players) <= 2 or i >= 2:
                        start = time.time()
                        image: Coroutine[Any, Any, discord.File] = await asyncio.to_thread(
                            self.cog.generate_image, user_1=killer, user_2=killed, to_file=True
                        )
                        end = time.time()
                        delay = self.delay - (end - start)
                        await asyncio.sleep(delay)
                        embed: discord.Embed = discord.Embed(
                            title="Battle Royale", color=await self.ctx.embed_color()
                        )
                        embed.description = (
                            f"{prompts}"
                            f"\n\n**{len(self.remaining_players)} Remaining Players**\n"
                        )[:2000]
                        embed.set_image(url="attachment://image.png")
                        _view = RemainingPlayerView(
                            remaining=self.remaining_players,
                            color=await self.ctx.embed_color(),
                        )
                        if EDIT_ORIGINAL_MESSAGE:
                            _message = await self.original_message.edit(
                                embed=embed, attachments=[await image], view=_view
                            )
                            _view._message = _message

                        else:
                            _message = await self.ctx.send(
                                embed=embed, files=[await image], view=_view
                            )
                            _view._message = _message
                        prompts = ""
                        i = 0
                    else:
                        i += 1

        winner = self.remaining_players[0]
        places.insert(0, winner)
        places_text = "".join(
            f"**#{index}** - {player.global_name or player.display_name} - {kills[player]} kill{'s' if kills[player] > 1 else ''}\n"
            for index, player in enumerate(places[:10], start=1)
        )
        places_text = list(pagify(places_text, page_length=2000))[0]
        embed: discord.Embed = discord.Embed(
            title="BattleRoyale",
            color=await self.ctx.embed_color(),
        )
        winner_prompt = random.choice(WINNER_PROMPTS).format(winner=f"**{winner.display_name}**")
        currency = await bank.get_currency_name(self.ctx.guild)
        amount = await self.cog.config.guild(ctx.guild).prize()
        try:
            await bank.deposit_credits(winner, amount)
            payout_message = f"- {str(winner)} recieved {int(amount)} {currency}."
        except BalanceTooHigh as e:
            await bank.set_balance(winner, e.max_balance)
            payout_message = f"{winner} has max balance!"
        embed.description = f"{winner_prompt}\n{payout_message}\n\n**Places:**\n{places_text}"[
            :1900
        ]
        if EDIT_ORIGINAL_MESSAGE:
            await self.original_message.edit(embed=embed)
        else:
            await self.ctx.send(embed=embed)
        await self.cog.add_stats_to_leaderboard("wins", users=[winner])
        await self.cog.add_exp_and_maybe_update_level(winner)
        return winner
