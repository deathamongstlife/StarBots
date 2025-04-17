import json
from pathlib import Path

from starbot.core.bot import Red

from .core import ToDo

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    await bot.add_cog(ToDo(bot))
