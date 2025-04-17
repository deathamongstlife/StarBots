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

import functools
from typing import Callable, Dict, List, Optional, Union

import discord
from starbot.core import commands
from starbot.core.bot import Red

select_options: Dict[str, Dict[str, str]] = {
    "en": {
        "label": "English",
        "description": "Get English translation of this question.",
    },
    "bn": {
        "label": "Bengali",
        "description": "Get Bengali translation of this question.",
    },
    "de": {
        "label": "German",
        "description": "Get German translation of this question.",
    },
    "es": {
        "label": "Spanish",
        "description": "Get Spanish translation of this question.",
    },
    "fr": {
        "label": "French",
        "description": "Get French translation of this question.",
    },
    "hi": {
        "label": "Hindi",
        "description": "Get Hindi translation of this question.",
    },
    "tl": {
        "label": "Filipino",
        "description": "Get French translation of this question.",
    },
}


class BaseLanguageOptions:
    def __init__(self) -> None:
        self._options: List[discord.SelectOption] = [
            discord.SelectOption(
                value=key,
                label=select_options[key]["label"],
                description=select_options[key]["description"],
            )
            for key in select_options
        ]

    def __call__(self) -> List[discord.SelectOption]:
        return self._options

    @classmethod
    def _get_options(cls) -> List[discord.SelectOption]:
        self = cls()
        return self._options


class Select(discord.ui.Select):
    def __init__(
        self,
        callback: Callable[["Select", discord.Interaction], None],
    ) -> None:
        options: List[discord.SelectOption] = BaseLanguageOptions()()
        super().__init__(
            placeholder="Translations",
            options=options,
            max_values=1,
            min_values=1,
        )
        self.callback: functools.partial = functools.partial(callback, self)  # type: ignore


class CGView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context,
        result: Dict[str, Union[str, Dict[str, str]]],
        member: Optional[discord.Member] = None,
        timeout: Optional[float] = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self._ctx: commands.Context = ctx
        self._result: Dict[str, Union[str, Dict[str, str]]] = result
        self._member: Optional[discord.Member] = member
        self._message: Optional[discord.Message] = None

        self.add_item(Select(self._callback))  # type: ignore

    async def on_timeout(self) -> None:
        for item in self.children:
            item: discord.ui.Item
            item.disabled = True  # type: ignore
        try:
            await self._message.edit(view=self)  # type: ignore
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction[Red]) -> bool:  # type: ignore
        if (
            self._member.id != interaction.user.id
            if self._member is not None
            else self._ctx.author.id != interaction.user.id
        ):
            await interaction.response.send_message(
                "You are not allowed to use this interaction", ephemeral=True
            )
            return False
        return True

    @staticmethod
    async def _callback(self: Select, interaction: discord.Interaction[Red]) -> None:  # type: ignore
        await interaction.response.defer()
        title: Optional[str] = (
            f"{self.view._ctx.author} asked {self.view._member}"  # type: ignore
            if self.view._member is not None  # type: ignore
            else None
        )
        embed: discord.Embed = discord.Embed(
            title=title,
            description=(
                self.view._result["question"]  # type: ignore
                if self.values[0] == "English"
                else f"({select_options[self.values[0]]['label']}) {self.view._result['translations'][self.values[0]]}"  # type: ignore
            ),
            color=await self.view._ctx.embed_color(),  # type: ignore
        )
        embed.set_footer(
            text=f"Rating: {self.view._result['rating']} | ID: {self.view._result['id']}"  # type: ignore
        )
        await interaction.edit_original_response(embed=embed)
