import asyncio
from typing import Optional
from Star-Utils import Cog, CogsUtils

import discord
from starbot.core import Config, checks, commands, i18n
from starbot.core.bot import Red


class OnEdit(Cog):
    async def red_get_data_for_user(self, *, user_id):
        return {}  # No data to get

    async def red_delete_data_for_user(self, *, requester, user_id):
        pass  # No data to delete

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2_113_674_295, force_registration=True)
        self.config.register_global(timeout=5)
        self.timeout: Optional[float] = None

    async def edit_process_commands(self, before: discord.Message, after: discord.Message):
        """Same as Red's method (Red.process_commands), but dont dispatch message_without_command."""
        ctx: Optional[commands.Context]
        if not after.author.bot:
            ctx = await self.bot.get_context(after)
            assert ctx
            await self.bot.invoke(ctx)
            if ctx.valid is False:
                # My Act and Phen's Tags use on_command_error, and thus aren't needed in this list.
                for allowed_name in ("Alias", "CustomCommands", "CCRoles"):
                    cog = self.bot.get_cog(allowed_name)
                    if not cog:
                        continue
                    for name, listener in cog.get_listeners():
                        if name != "on_message_without_command":
                            continue
                        asyncio.ensure_future(listener(after))  # noqa: RUF006
        else:
            ctx = None
        if ctx is None or ctx.valid is False:
            self.bot.dispatch("message_edit_without_command", before, after)

    @commands.command()
    @checks.is_owner()
    async def edittime(self, ctx: commands.Context, *, timeout: float):
        """
        Change how long the bot will listen for message edits to invoke as commands.

        Defaults to 5 seconds.
        Set to 0 to disable.
        """
        timeout = max(timeout, 0)
        await self.config.timeout.set(timeout)
        self.timeout = timeout
        await ctx.tick()

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.edited_at:
            return
        if before.content == after.content:
            return
        if await self.bot.cog_disabled_in_guild(self, after.guild):
            return
        if self.timeout is None:
            self.timeout = await self.config.timeout()
        if (after.edited_at - after.created_at).total_seconds() > self.timeout:
            return
        await i18n.set_contextual_locales_from_guild(self.bot, after.guild)
        await self.edit_process_commands(before, after)
