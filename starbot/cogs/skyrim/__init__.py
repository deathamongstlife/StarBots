from starbot.core.bot import Red
from starbot.core.utils import get_end_user_data_statement_or_raise

__red_end_user_data_statement__ = get_end_user_data_statement_or_raise(__file__)

from .skyrim import Skyrim


async def setup(bot: Red):
    await bot.add_cog(Skyrim(bot))
