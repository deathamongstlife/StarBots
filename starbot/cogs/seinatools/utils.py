"""
MIT License

Copyright (c) 2022-present japandotorg

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

import logging
from typing import TYPE_CHECKING, Any, Dict, Final, List, Type, Union

from emoji import EMOJI_DATA  # type: ignore
from starbot.core import commands  # type: ignore

log: logging.Logger = logging.getLogger("red.seinacogs.tools.utils")

__all__: List[str] = [
    "Emoji",
    "EmojiConverter",
    "CRATES_IO_LOGO",
    "NPM_LOGO",
    "RUBY_GEMS_LOGO",
]

NoneType: Type[None] = type(None)

CRATES_IO_LOGO: Final[str] = "https://avatars.githubusercontent.com/u/76801495?s=280&v=4"

NPM_LOGO: Final[str] = "https://avatars.githubusercontent.com/u/6078720?s=200&v=4"

RUBY_GEMS_LOGO: Final[str] = "https://avatars.githubusercontent.com/u/208761?s=200&v=4"


class Emoji:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.name = data["name"]
        self.id = data.get("id", None)
        self.animated = data.get("animated", None)
        self.custom = self.id is not None

    @classmethod
    def from_data(cls, data: Union[str, Dict[str, Any]]):
        log.debug(data)
        if not data:
            return None
        if isinstance(data, str):
            return cls({"name": data})
        return cls(data)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "id": self.id}

    def as_emoji(self) -> str:
        if not self.custom:
            return self.name
        animated = "a" if self.animated else ""
        return f"<{animated}:{self.name}:{self.id}>"


if TYPE_CHECKING:
    EmojiConverter = Union[Emoji, NoneType]
else:

    class EmojiConverter(commands.PartialEmojiConverter):
        async def convert(self, ctx: commands.Context, arg: str) -> Union[Emoji, NoneType]:
            if arg.lower() == "none":
                return None
            arg = arg.strip()
            data = arg if arg in EMOJI_DATA.keys() else await super().convert(ctx, arg)
            data = getattr(data, "to_dict", lambda: data)()
            return Emoji.from_data(data)
