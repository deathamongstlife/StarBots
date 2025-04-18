import io

import black
import discord
from starbot.core import commands
from starbot.core.bot import Red
from typing import Optional
from Star-Utils import Cog, CogsUtils

class BlackFormatter(Cog):
    """Run black on code."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.logs = CogsUtils.get_logger("Black")

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.has_permissions(attach_files=True)
    @commands.command(name="black", usage=f"<file> [line_length=None]")
    async def _black(self, ctx: commands.Context, line_length: Optional[int] = None):
        """Format a python file with black.

        You need to attach a file to this command, and it's extension needs to be `.py`.
        Your `line_length` is black setting. If it is not provided, it defaults to the
        configured black line length (the default, unchanged, is 88).
        """
        await ctx.typing()
        if not ctx.message.attachments:
            return await ctx.send_help()
        attachment_file = ctx.message.attachments[0]
        if not attachment_file.filename.lower().endswith(".py"):
            return await ctx.send("Must be a python file.")

        file = await attachment_file.read()
        try:
            sort = file.decode(encoding="utf-8")
        except UnicodeDecodeError:
            return await ctx.send("Something went wrong when trying to decode this file.")

        try:
            output = black.format_file_contents(
                sort,
                fast=True,
                mode=black.FileMode(line_length=line_length or black.DEFAULT_LINE_LENGTH),
            )
        except black.NothingChanged:
            await ctx.send("There was nothing to change in this code.")
        else:
            await ctx.send(
                content="See the attached file below, with your formatted code.",
                file=discord.File(
                    io.BytesIO(output.encode(encoding="utf-8")),
                    filename=attachment_file.filename.lower(),
                ),
            )
