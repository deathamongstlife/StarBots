from starbot.core.bot import Red
from starbot.core.utils import get_end_user_data_statement

from .main import TierLists

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Red):
    cog = TierLists(bot)
    await bot.add_cog(cog)
