import requests
import asyncio
from starbot.core import commands, Config, checks
from starbot.core.bot import Red
from Star_Utils import Cog

class LicenseVerification(Cog):
    """Cog that checks license validity periodically before allowing command execution."""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=205192943327321000143939875896557571750, force_registration=True)
        default_global = {
            "licenseKey": None,
            "productName": None,
            "isValid": False,
        }
        self.config.register_global(**default_global)
        self.bot.add_check(self.bot_check)
        self.bg_task = self.bot.loop.create_task(self.periodic_license_check())

    def cog_unload(self):
        self.bot.remove_check(self.bot_check)
        self.bg_task.cancel()

    async def validate_license(self):
        """Validate the license key with the server."""
        licenseKey = await self.config.licenseKey()
        productName = await self.config.productName()
        url = "http://195.58.58.45:3005/api/client"
        api_key = "3oLySDo9XhATNamnyCIpi7Ybh&nfdN?&"

        headers = {
            "Authorization": api_key,
        }
        data = {
            "licensekey": licenseKey,
            "product": productName,
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            status = response.json()

            if status.get("status_overview") == "success":
                await self.config.isValid.set(True)
                print("Your license key is valid!")
                print("Discord ID: " + status.get('discord_id', 'N/A'))
                return True
            else:
                await self.config.isValid.set(False)
                print("Your license key is invalid!")
                print("Create a ticket in our discord server to get one.")
                return False
        except requests.RequestException as e:
            print(f"Error: {e}")
            return False

    async def periodic_license_check(self):
        """Periodically check the license validity every 30 seconds."""
        await self.bot.wait_until_red_ready()
        while True:
            await self.validate_license()
            await asyncio.sleep(30)

    @commands.command()
    @checks.is_owner()
    async def setlicense(self, ctx: commands.Context):
        """Set the license key."""
        await ctx.send("Please enter the license key:")
        licenseKey = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author)
        await self.config.licenseKey.set(licenseKey.content)

        if await self.validate_license():
            await ctx.send("License validated successfully!")
        else:
            await ctx.send("License validation failed. Please check your keys and try again.")

    @commands.command()
    @checks.is_owner()
    async def setproduct(self, ctx: commands.Context):
        """Set the product name."""
        await ctx.send("Please enter the product name:")
        productName = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author)
        await self.config.productName.set(productName.content)
        await ctx.send("Product name set successfully!")

    async def bot_check(self, ctx: commands.Context) -> bool:
        """Check the license validity before executing any command."""
        if ctx.command.name in ["setlicense", "setproduct"]:
            return True
        if await self.config.isValid():
            return True
        await ctx.send("License is not valid or not set. Please use the `setlicense` command to set your license.")
        raise commands.CheckFailure("License is not valid or not set.")

async def setup(bot: Red):
    await bot.add_cog(LicenseVerification(bot))
