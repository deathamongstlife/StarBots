"""
MIT License

Copyright (c) 2020-2023 PhenoM4n4n
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

import asyncio
import logging
from typing import Any, Coroutine, Dict, Final, List, Literal, Optional, TypeAlias, Union

from starbot.core import commands
from starbot.core.bot import Red
from starbot.core.config import Config
from starbot.core.modlog import register_casetype
from starbot.core.utils.chat_formatting import humanize_list
from Star-Utils import Cog
from .abc import CompositeMetaClass
from .autorole import AutoRoles
from .reactroles import ReactRoles
from .roles import Roles

log: logging.Logger = logging.getLogger("red.seina.roleutils")

RequestType: TypeAlias = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class RoleUtils(
    Roles,
    AutoRoles,
    ReactRoles,
    Cog,
    metaclass=CompositeMetaClass,
):
    """
    Useful role commands.

    Includes massroling, role targeting, autoroling and reaction roles.
    """

    def __init__(self, bot: Red, *_args: Any) -> None:
        self.bot: Red = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=326235423452394523,
            force_registration=True,
        )

        default_guild: Dict[
            str, Dict[str, Union[List[int], bool, Dict[str, Union[List[int], bool]]]]
        ] = {
            "reactroles": {"channels": [], "enabled": True},
            "autoroles": {
                "toggle": False,
                "roles": [],
                "bots": {
                    "toggle": False,
                    "roles": [],
                },
                "humans": {
                    "toggle": False,
                    "roles": [],
                },
            },
        }
        default_role: Dict[str, bool] = {
            "sticky": False,
        }
        default_member: Dict[str, List[int]] = {
            "sticky_roles": [],
        }
        self.config.register_guild(**default_guild)
        self.config.register_role(**default_role)
        self.config.register_member(**default_member)

        default_guildmessage: Dict[str, Dict[str, Any]] = {"reactroles": {"react_to_roleid": {}}}
        self.config.init_custom("GuildMessage", 2)
        self.config.register_custom("GuildMessage", **default_guildmessage)

        self.initialize_task: asyncio.Task[Any] = self.create_task(self.initialize())

        self.register_cases: asyncio.Task[Any] = self.create_task(self._register_cases())

        self.cache: Dict[str, Any] = {}

        super().__init__(*_args)

    async def initialize(self) -> None:
        log.debug("RoleUtils initialize")
        await super().initialize()

    async def _register_cases(self) -> None:
        await self.bot.wait_until_red_ready()
        await self._register_casetype()

    @staticmethod
    async def _register_casetype() -> None:
        autorole: Dict[str, Union[str, bool]] = {
            "name": "autorole",
            "default_setting": True,
            "image": "✔️",
            "case_str": "Auto Role",
        }
        try:
            await register_casetype(**autorole)
        except RuntimeError:
            pass

    @staticmethod
    def task_done_callback(task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            log.exception("Task failed.", exc_info=error)

    def create_task(
        self, coroutine: Coroutine, *, name: Optional[str] = None
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        task.add_done_callback(self.task_done_callback)
        return task
