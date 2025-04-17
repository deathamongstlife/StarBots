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

from importlib import reload
from typing import Final, List, Optional

from starbot.core.bot import Red
from starbot.core.errors import CogLoadError

PIP: Final[str] = "pip(3)"


RESTRICTED_ATTRIBUTES: Final[List[str]] = [
    "{member(roleids)}",
    "{author(roleids)}",
    "{member(banner)}",
    "{author(banner)}",
    "{member(avatar)}",
    "{author(avatar)}",
    "{member(boost)}",
    "{author(boost)}",
    "{member(color)}",
    "{author(color)}",
    "{member(mention)}",
    "{author(mention)}",
    "{member(timed_out)}",
    "{author(timed_out)}",
    "{member(created_at)}",
    "{author(created_at)}",
    "{member(timestamp)}",
    "{author(timestamp)}",
    "{member(joined_at)}",
    "{author(joined_at)}",
    "{member(joinstamp)}",
    "{author(joinstamp)}",
    "{guild(icon)}",
    "{server(icon)}",
    "{guild(created_at)}",
    "{server(created_at)}",
    "{guild(timestamp)}",
    "{server(timestamp)}",
    "{guild(owner_id)}",
    "{server(owner_id)}",
    "{guild(description)}",
    "{server(description)}",
    "{guild(random)}",
    "{server(random)}",
]


def check_for_restricted_attributes(string: str) -> Optional[List[str]]:
    return [attribute for attribute in RESTRICTED_ATTRIBUTES if attribute in string] or None


async def validate_tagscriptengine(bot: Red, tse_version: str, *, reloaded: bool = False) -> None:
    try:
        import TagScriptEngine as tse
    except ImportError as exc:
        raise CogLoadError(
            "The ThreadOpener cog failed to install AdvancedTagScriptEngine. Reinstall the cog and restart your "
            "bot. If it continues to fail to load, contact the cog author."
        ) from exc

    commands = [
        f"`{PIP} uninstall -y TagScript`",
        f"`{PIP} uninstall -y TagScriptEngine`",
        f"`{PIP} uninstall -y AdvancedTagScriptEngine`",
        f"`{PIP} install AdvancedTagScriptEngine=={tse_version}`",
    ]
    commands = "\n".join(commands)

    message = (
        "The ThreadOpener cog attempted to install TagScriptEngine, but the version installed "
        "is outdated. Shut down your bot, then in shell in your venv, run the following "
        f"commands:\n{commands}\nAfter running these commands, restart your bot and reload "
        "Tags. If it continues to fail to load, contact the cog author."
    )

    if not hasattr(tse, "VersionInfo"):
        if not reloaded:
            reload(tse)
            await validate_tagscriptengine(bot, tse_version, reloaded=True)
            return

        await bot.send_to_owners(message)
        raise CogLoadError(message)

    if tse.version_info < tse.VersionInfo.from_str(tse_version):
        await bot.send_to_owners(message)
        raise CogLoadError(message)
