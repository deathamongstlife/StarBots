from .main import BoosterRoles


async def setup(bot):
    await bot.add_cog(BoosterRoles(bot))
