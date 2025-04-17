import asyncio
import logging
import typing as t

from starbot.core import Config, commands
from starbot.core.bot import Red
from Star-Utils import Cog
from .abc import CompositeMetaClass
from .commands import Commands
from .common.models import DB
from .views import VoteSelect

log = logging.getLogger("red.bounty.tierlists")
RequestType = t.Literal["discord_deleted_user", "owner", "user", "user_strict"]


class TierLists(Commands, Cog, metaclass=CompositeMetaClass):
    """Create different tierlists that users can add options to and vote on."""

        
    def __init__(self, bot: Red):
        super().__init__(bot)
        self.bot: Red = bot
        self.config = Config.get_conf(self, 117, force_registration=True)
        self.config.register_global(db={})

        self.db: DB = DB()
        self.saving = False

    async def cog_load(self) -> None:
        asyncio.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        data = await self.config.db()
        self.db = await asyncio.to_thread(DB.model_validate, data)
        self.bot.add_dynamic_items(VoteSelect)
        log.info("Config loaded")

    async def save(self) -> None:
        if self.saving or not self.db:
            return
        try:
            self.saving = True
            dump = await asyncio.to_thread(self.db.model_dump, mode="json")
            await self.config.db.set(dump)
        except Exception as e:
            log.exception("Failed to save config", exc_info=e)
        finally:
            self.saving = False

    async def cog_unload(self):
        await self.save()
        self.bot.remove_dynamic_items(VoteSelect)
        log.info("Config saved")
