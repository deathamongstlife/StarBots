from Star-Utils import Cog, CogsUtils  # isort:skip
from starbot.core import commands  # isort:skip
from starbot.core.bot import Red  # isort:skip
from starbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import SplitOrStealGameView

# Credits:
# General repo credits.
# Thanks to Lemon for the cog idea!

_: Translator = Translator("SplitOrStealGame", __file__)


@cog_i18n(_)
class SplitOrStealGame(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.logs = CogsUtils.get_logger("SplitOrStealGame")
    """A cog to play a match of Split Or Steal game!"""

    @property
    def games(self) -> typing.Dict[discord.Message, SplitOrStealGameView]:
        return self.views

    @commands.guild_only()
    @commands.hybrid_command(aliases=["splitorsteal", "sosg", "sos"])
    async def splitorstealgame(self, ctx: commands.Context) -> None:
        """
        Play a match of Split Or Steal game.

        Two player will have to click the button that they choose (`split` or `steal`).
        • If both choose `split` both of them win.
        • If both choose `steal`, both loose.
        • if one chooses `split` and one chooses `steal`, the one who choose `steal` will win.
        """
        await SplitOrStealGameView(cog=self).start(ctx)
