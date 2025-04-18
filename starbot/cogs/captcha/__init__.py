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

import json
import re
from pathlib import Path
from typing import Match, Optional, Pattern

from starbot.core.bot import Red
from starbot.core.errors import CogLoadError

from ._tagscript import validate_tagscriptengine
from .core import Captcha

VERSION_RE: Pattern[str] = re.compile(r"AdvancedTagScriptEngine==(\d\.\d\.\d)")

with open(Path(__file__).parent / "info.json") as f:
    data = json.load(f)

tse_version = None
for requirement in data.get("requirements", []):
    match: Optional[Match[str]] = VERSION_RE.search(requirement)
    if match:
        tse_version = match.group(1)
        break

if not tse_version:
    raise CogLoadError(
        "Failed to find TagScriptEngine version number. Please report this to the cog author."
    )


async def setup(bot: Red) -> None:
    await validate_tagscriptengine(bot, tse_version)
    cog = Captcha(bot)
    await bot.add_cog(cog)
