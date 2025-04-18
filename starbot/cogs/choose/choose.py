import logging
import random
from re import split
from Star-Utils import Cog, CogsUtils

import discord
from starbot.core import commands
from starbot.core.bot import Red

log = logging.getLogger("red.raidensakura.choose")


class Choose(Cog):
    """
    A better replacement for core `choose` command.
    Supports multiple delimiters: `;`, `,`, `\\n`, `|`, and `#`
    """

        
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        global old_choose
        if old_choose:
            try:
                self.bot.remove_command("choose")
            except:
                pass
            self.bot.add_command(old_choose)


    async def red_delete_data_for_user(self, **kwargs) -> None:
        """Nothing to delete"""
        return

    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["pick, choice"])
    async def choose(self, ctx, *, options):
        """
        Choose between multiple options.
        There must be at least 2 options to pick from.
        Supports multiple separators: `;`, `,`, `\\n`, `|`, and `#`
        """

        choosearray = split(r";|,|\n|\||#", options)

        if len(choosearray) > 1:
            e = discord.Embed(
                color=(await ctx.embed_colour()), title=random.choice(choosearray)
            )
            e.set_footer(
                text=f"✨ Choosing for {ctx.author.display_name}, from a list of {len(choosearray)} options."
            )
        else:
            return await ctx.send("Not enough options to pick from.")

        try:
            return await ctx.send(embed=e)
        except Exception as exc:
            log.exception("Error trying to send choose embed.", exc_info=exc)
            return await ctx.send(
                "Oops, I encountered an error while trying to send the embed."
            )


async def setup(bot: Red) -> None:
    global old_choose
    old_choose = bot.get_command("choose")
    if old_choose:
        bot.remove_command(old_choose.name)

    cog = Choose(bot)

    r = bot.add_cog(cog)
    if r is not None:
        await r
