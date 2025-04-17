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

from typing import Any, Dict, Final, List, Optional, final

import discord
import TagScriptEngine as tse
from starbot.core import commands
from starbot.core.utils.chat_formatting import humanize_list, humanize_number

from .utils import check_for_restricted_attributes

default_thread_name: str = "{author(name)}:{counter}"
thread_message: str = """
{embed(description):Welcome to the thread.}
{embed(thumbnail):{member(avatar)}}
{embed(color):{color}}
"""

TAGSCRIPT_LIMIT: Final[int] = 10_000

blocks: List[tse.Block] = [
    tse.LooseVariableGetterBlock(),
    tse.AssignmentBlock(),
    tse.CommandBlock(),
    tse.EmbedBlock(),
    tse.IfBlock(),
]

tagscript_engine: tse.Interpreter = tse.Interpreter(blocks)


def process_tagscript(content: str, seed_variables: Dict[str, tse.Adapter] = {}) -> Dict[str, Any]:
    output: tse.Response = tagscript_engine.process(content, seed_variables)
    kwargs: Dict[str, Any] = {}
    if output.body:
        kwargs["content"] = discord.utils.escape_mentions(output.body[:2000])
    if embed := output.actions.get("embed"):
        kwargs["embed"] = embed
    return kwargs


class TagError(Exception):
    """
    Base exception class.
    """


@final
class TagCharacterLimitReached(TagError):
    """Raised when the TagScript character limit is reached."""

    def __init__(self, limit: int, length: int):
        super().__init__(
            f"TagScript cannot be longer than {humanize_number(limit)} (**{humanize_number(length)}**)."
        )


@final
class TagScriptConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        try:
            await ctx.cog.validate_tagscript(argument)  # type: ignore
        except TagError as e:
            raise commands.BadArgument(str(e))
        return argument


class DefaultNameConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument: str = await TagScriptConverter().convert(ctx, argument)
        if len(argument) <= 0 and len(argument) > 40:
            raise commands.BadArgument(
                "Argument must be between 0 and 40 characters long, recieved {} instead.".format(
                    len(argument)
                )
            )
        denied: Optional[List[str]] = check_for_restricted_attributes(argument)
        if denied and len(denied) > 0:
            raise commands.BadArgument(
                "Using {} is not allowed in this context.".format(humanize_list(denied))
            )
        return argument
