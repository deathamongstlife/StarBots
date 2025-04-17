from starbot.core import errors  # isort:skip
import importlib
import sys

try:
    import Star-Utils
except ModuleNotFoundError:
    raise errors.CogLoadError(
        "The needed utils to run the cog were not found. Please execute the command `[p]pipinstall git+https://github.com/LeDeathAmongst/Star-Utils.git`. A restart of the bot isn't necessary."
    )
modules = sorted(
    [module for module in sys.modules if module.split(".")[0] == "Star-Utils"], reverse=True
)
for module in modules:
    try:
        importlib.reload(sys.modules[module])
    except ModuleNotFoundError:
        pass
del Star-Utils
# import Star-Utils
# import json
# import os
# # with open(os.path.join(os.path.dirname(__file__), "utils_version.json"), mode="r") as f:
#     data = json.load(f)
# needed_utils_version = data["needed_utils_version"]
# if __version__ > needed_utils_version:
#     raise errors.CogLoadError(
#         "The needed utils to run the cog has a higher version than the one supported by this version of the cog. Please update the cogs of the `StarCogs` repo."
#     )
# elif __version__ < needed_utils_version:
#     raise errors.CogLoadError(
#         "The needed utils to run the cog has a lower version than the one supported by this version of the cog. Please execute the command `[p]pipinstall --upgrade git+https://github.com/LeDeathAmongst/Star-Utils.git`. A restart of the bot isn't necessary."
#     )

from starbot.core.bot import Red  # isort:skip
import asyncio
import builtins
import typing

import rich
from starbot.core.utils import get_end_user_data_statement
from starbot.core.utils.chat_formatting import humanize_list

from .dev import Dev
from .env import ctxconsole

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

original_sys_displayhook = None
original_rich_get_console = None


async def setup_after_ready(bot: Red) -> None:
    await bot.wait_until_red_ready()

    def _displayhook(obj: typing.Any) -> None:
        if obj is not None:
            _console = ctxconsole.get()
            builtins._ = None
            rich.pretty.pprint(obj, console=_console)
            builtins._ = obj

    def _get_console() -> rich.console.Console:
        return ctxconsole.get()

    global original_sys_displayhook
    original_sys_displayhook = sys.displayhook
    sys.displayhook = _displayhook
    global original_rich_get_console
    original_rich_get_console = rich.get_console
    rich.get_console = _get_console


async def setup(bot: Red) -> None:
    if not bot._cli_flags.dev:
        raise errors.CogLoadError("This cog requires the `--dev` CLI flag.")
    cog = Dev(bot)
    if (core_dev := bot.get_cog("Dev")) is not None:
        if (env_extensions := getattr(core_dev, "env_extensions", None)) is not None:
            cog.env_extensions = env_extensions
        if (source_cache := getattr(core_dev, "source_cache", None)) is not None:
            cog.source_cache = source_cache
        if (dev_space := getattr(core_dev, "dev_space", None)) is not None:
            cog.dev_space = dev_space
        if (_last_result := getattr(core_dev, "_last_result", None)) is not None:
            cog._last_result = _last_result
        # if (sessions := getattr(core_dev, "sessions", None)) is not None:
        #     cog.sessions = sessions
        if sessions := getattr(core_dev, "sessions", None):
            s = "s" if len(sessions) > 1 else ""
            is_private = bot._connection._private_channels.__contains__
            raise errors.CogLoadError(
                f"End your REPL session{s} first: "
                + humanize_list(
                    ["Private channel" if is_private(id) else f"<#{id}>" for id in sessions]
                )
            )
    await bot.remove_cog("Dev")
    await bot.add_cog(cog)
    asyncio.create_task(setup_after_ready(bot))


async def teardown(bot: Red) -> None:
    if original_sys_displayhook is not None:
        sys.displayhook = original_sys_displayhook
    if original_rich_get_console is not None:
        rich.get_console = original_rich_get_console
