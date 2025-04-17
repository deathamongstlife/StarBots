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

import random
from functools import partial
from typing import Any, Dict, List, Optional

import discord
from starbot.core.bot import Red
from starbot.core.utils.chat_formatting import pagify
from starbot.core.utils.views import SimpleMenu

__all__ = ("JoinGameView",)


class InteractionSimpleMenu(SimpleMenu):
    async def inter(self, interaction: discord.Interaction[Red]) -> None:
        await interaction.response.defer()
        self._fallback_author_to_ctx = False
        self.author: discord.abc.User = interaction.user
        kwargs: Dict[str, Any] = await self.get_page(self.current_page)
        self.message: discord.Message = await interaction.followup.send(**kwargs, ephemeral=True)


class RemainingPlayerButton(discord.ui.Button):
    def __init__(
        self,
        callback: Any,
        custom_id: str = "REMAINING_PLAYER:BUTTON",
        emoji: Optional[str] = None,
    ) -> None:
        super().__init__(
            label="Remaining Players",
            emoji=emoji,
            custom_id=custom_id,
        )
        self.callback: partial = partial(callback, self)


class JoinGameButton(discord.ui.Button):
    def __init__(self, emoji: Optional[str], callback: Any, custom_id: str = "JOIN_GAME:BUTTON"):
        super().__init__(
            label="Join Game",
            emoji=emoji,
            custom_id=custom_id,
        )
        self.callback = partial(callback, self)


class JoinGameView(discord.ui.View):
    def __init__(self, emoji: Optional[str], timeout: float = 120) -> None:
        super().__init__(timeout=timeout)
        self.players: List[discord.Member] = []
        self._message: discord.Message = None

        self.add_item(JoinGameButton(emoji, self._callback))

    async def on_timeout(self) -> None:
        for item in self.children:
            item: discord.ui.Item
            item.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @staticmethod
    async def _callback(self: JoinGameButton, interaction: discord.Interaction) -> None:
        if len(self.view.players) > 200:
            await interaction.response.send_message(
                "The maximum number of 200 players has been reached.",
                ephemeral=True,
            )
            return
        elif interaction.user in self.view.players:
            await interaction.response.send_message(
                "You have already joined this game!",
                ephemeral=True,
            )
            return
        else:
            self.view.players.append(interaction.user)
            await interaction.response.send_message(
                "You have joined this game!",
                ephemeral=True,
            )


class RemainingPlayerView(discord.ui.View):
    def __init__(
        self,
        remaining: List[discord.Member],
        color: discord.Color,
        emoji: Optional[str] = None,
        timeout: float = 45,
    ) -> None:
        super().__init__(timeout=timeout)
        self.remaining: List[discord.Member] = remaining
        self.color: discord.Color = color
        self._message: Optional[discord.Message] = None

        self.add_item(RemainingPlayerButton(self._callback, emoji=emoji))

    async def on_timeout(self) -> None:
        for item in self.children:
            item: discord.ui.Item
            item.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @staticmethod
    async def _callback(
        self: RemainingPlayerButton, interaction: discord.Interaction[Red]
    ) -> None:
        players: List[discord.Member] = list(self.view.remaining).copy()
        if not players:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="There are not remaining players!",
                    color=self.view.color,
                )
            )
            return
        random.shuffle(players)
        remaining: str = "\n".join(
            "{}. {} ( `{}` )".format(idx, player.mention, player.id)
            for idx, player in enumerate(players)
        )
        embeds: List[discord.Embed] = []
        for page in list(pagify(remaining)):
            embed: discord.Embed = discord.Embed(
                title="Remaining Players",
                description=page,
                color=self.view.color,
            )
            embeds.append(embed)
        await InteractionSimpleMenu(pages=embeds).inter(interaction)
