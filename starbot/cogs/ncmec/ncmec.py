import discord #type: ignore
from starbot.core import commands #type: ignore
import aiohttp #type: ignore
import asyncio
import json
import datetime
from Star-Utils import Cog, CogsUtils

class MissingKids(Cog):
    """Cog to interact with the National Center for Missing and Exploited Children"""

    def __init__(self, bot):
        self.bot = bot
        self.dm_alerts_enabled = {}  # Dictionary to store user preferences for DM alerts
        self.last_checked = datetime.datetime.utcnow()  # Track the last time we checked for new records

    @commands.group()
    async def ncmec(self, ctx):
        """Primary command group"""
        pass

    @ncmec.command()
    async def dm(self, ctx):
        """Toggle DM alerts for new missing persons"""
        user_id = ctx.author.id
        if self.dm_alerts_enabled.get(user_id):
            self.dm_alerts_enabled[user_id] = False
            embed = discord.Embed(
                title="DM alerts disabled",
                description="DM alerts for new missing persons have been disabled.",
                color=0xff4545
            )
        else:
            self.dm_alerts_enabled[user_id] = True
            embed = discord.Embed(
                title="DM alerts enabled",
                description="DM alerts for new missing persons have been enabled.",
                color=0x2bbd8e
            )
        await ctx.send(embed=embed)

    async def check_for_new_records(self):
        """Check for new missing records and send DMs to users who have enabled alerts"""
        base_url = "https://api.missingkids.org/missingkids/servlet/JSONDataServlet?action=publicSearch&goToPage={}"
        headers = {"Accept": "application/json"}
        page = 1
        new_records = []

        async with aiohttp.ClientSession() as session:
            while True:
                url = base_url.format(page)
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return

                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        text_data = await response.text()
                        try:
                            data = json.loads(text_data)
                        except json.JSONDecodeError:
                            return

                    if not data.get("persons"):
                        break

                    for person in data["persons"]:
                        record_date = datetime.datetime.strptime(person.get('dateMissing'), '%Y-%m-%d')
                        if record_date > self.last_checked:
                            new_records.append(person)

                page += 1

        if new_records:
            self.last_checked = datetime.datetime.utcnow()
            for user_id, enabled in self.dm_alerts_enabled.items():
                if enabled:
                    user = self.bot.get_user(user_id)
                    if user:
                        for person in new_records:
                            embed = discord.Embed(
                                title=f"{person.get('firstName', '')} {person.get('middleName', '')} {person.get('lastName', '')}".strip(),
                                color=0xfffffe
                            )
                            if person.get('caseNumber'):
                                embed.add_field(name="Case number", value=person.get('caseNumber'), inline=False)
                            if person.get('orgName'):
                                embed.add_field(name="Issuing organization", value=person.get('orgName'), inline=False)
                            if person.get('firstName'):
                                embed.add_field(name="First name", value=person.get('firstName'), inline=True)
                            if person.get('middleName'):
                                embed.add_field(name="Middle name", value=person.get('middleName'), inline=True)
                            if person.get('lastName'):
                                embed.add_field(name="Last name", value=person.get('lastName'), inline=True)
                            if person.get('age'):
                                embed.add_field(name="Age", value=person.get('age'), inline=True)
                            if person.get('race'):
                                embed.add_field(name="Race", value=person.get('race'), inline=True)
                            if person.get('approxAge'):
                                embed.add_field(name="Estimated age", value=person.get('approxAge'), inline=True)
                            if person.get('missingCity'):
                                embed.add_field(name="Missing city", value=person.get('missingCity').title(), inline=True)
                            if person.get('missingCounty'):
                                embed.add_field(name="Missing county", value=person.get('missingCounty').title(), inline=True)
                            if person.get('missingState'):
                                state_code = person.get('missingState').upper()
                                state_full_name = {
                                    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
                                    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
                                    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
                                    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
                                    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
                                    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
                                    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
                                    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
                                    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
                                    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
                                }.get(state_code, state_code)
                                embed.add_field(name="Missing state", value=state_full_name, inline=True)
                            if person.get('missingCountry'):
                                embed.add_field(name="Missing country", value=person.get('missingCountry'), inline=False)
                            if person.get('missingDate'):
                                missing_date = person.get('missingDate')
                                try:
                                    timestamp = int(datetime.datetime.strptime(missing_date, '%Y-%m-%d').timestamp())
                                except ValueError:
                                    try:
                                        timestamp = int(datetime.datetime.strptime(missing_date, '%b %d, %Y %I:%M:%S %p').timestamp())
                                    except ValueError:
                                        continue  # Skip this record if date parsing fails
                                embed.add_field(
                                    name="Missing date", 
                                    value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", 
                                    inline=False
                                )
                            if person.get('caseType'):
                                embed.add_field(name="Case type", value=person.get('caseType'), inline=False)
                            thumbnail_url = person.get('thumbnailUrl')
                            if thumbnail_url:
                                embed.set_thumbnail(url=f"https://api.missingkids.org{thumbnail_url}")
                            try:
                                await user.send(embed=embed)
                            except discord.Forbidden:
                                continue  # Skip if the bot cannot send a DM to the user
                            except discord.HTTPException:
                                continue  # Skip if there is a network issue

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the background task to check for new records when the bot is ready"""
        self.bot.loop.create_task(self.background_task())

    async def background_task(self):
        """Background task to periodically check for new records"""
        while True:
            await self.check_for_new_records()
            await asyncio.sleep(3600)  # Check every hour
    
    @ncmec.command()
    async def list(self, ctx):
        """Show missing persons"""
        base_url = "https://api.missingkids.org/missingkids/servlet/JSONDataServlet?action=publicSearch&goToPage={}"
        headers = {"Accept": "application/json"}
        page = 1
        embeds = []

        async with aiohttp.ClientSession() as session:
            try:
                while True:
                    url = base_url.format(page)
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            await ctx.send("Failed to fetch data from the MissingKids API.")
                            return

                        try:
                            data = await response.json()
                        except aiohttp.ContentTypeError:
                            text_data = await response.text()
                            try:
                                data = json.loads(text_data)
                            except json.JSONDecodeError:
                                await ctx.send("Failed to parse the response from the MissingKids API.")
                                return

                        if not data.get("persons"):
                            break

                        for person in data["persons"]:
                            embed = discord.Embed(
                                title=f"{person.get('firstName', '')} {person.get('middleName', '')} {person.get('lastName', '')}".strip(),
                                color=0xfffffe
                            )
                            if person.get('caseNumber'):
                                embed.add_field(name="Case number", value=person.get('caseNumber'), inline=False)
                            if person.get('orgName'):
                                embed.add_field(name="Issuing organization", value=person.get('orgName'), inline=False)
                            if person.get('firstName'):
                                embed.add_field(name="First name", value=person.get('firstName'), inline=True)
                            if person.get('middleName'):
                                embed.add_field(name="Middle name", value=person.get('middleName'), inline=True)
                            if person.get('lastName'):
                                embed.add_field(name="Last name", value=person.get('lastName'), inline=True)
                            if person.get('age'):
                                embed.add_field(name="Age", value=person.get('age'), inline=True)
                            if person.get('race'):
                                embed.add_field(name="Race", value=person.get('race'), inline=True)
                            if person.get('approxAge'):
                                embed.add_field(name="Estimated age", value=person.get('approxAge'), inline=True)
                            if person.get('missingCity'):
                                embed.add_field(name="Missing city", value=person.get('missingCity').title(), inline=True)
                            if person.get('missingCounty'):
                                embed.add_field(name="Missing county", value=person.get('missingCounty').title(), inline=True)
                            if person.get('missingState'):
                                state_code = person.get('missingState').upper()
                                state_full_name = {
                                    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
                                    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
                                    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
                                    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
                                    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
                                    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
                                    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
                                    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
                                    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
                                    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
                                }.get(state_code, state_code)
                                embed.add_field(name="Missing state", value=state_full_name, inline=True)
                            if person.get('missingCountry'):
                                embed.add_field(name="Missing country", value=person.get('missingCountry'), inline=False)
                            if person.get('missingDate'):
                                missing_date = person.get('missingDate')
                                try:
                                    timestamp = int(datetime.datetime.strptime(missing_date, '%Y-%m-%d').timestamp())
                                except ValueError:
                                    try:
                                        timestamp = int(datetime.datetime.strptime(missing_date, '%b %d, %Y %I:%M:%S %p').timestamp())
                                    except ValueError:
                                        await ctx.send(f"Failed to parse the missing date: {missing_date}")
                                        continue
                                embed.add_field(
                                    name="Missing date", 
                                    value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", 
                                    inline=False
                                )
                            if person.get('caseType'):
                                embed.add_field(name="Case type", value=person.get('caseType'), inline=False)
                            thumbnail_url = person.get('thumbnailUrl')
                            if thumbnail_url:
                                embed.set_thumbnail(url=f"https://api.missingkids.org{thumbnail_url}")
                            embeds.append(embed)

                        if page >= data.get("totalPages", 1):
                            break
                        page += 1

                if not embeds:
                    await ctx.send("No recently missing children found.")
                    return

                for embed in embeds:
                    embed.set_footer(text=f"Total cases known: {len(embeds)}")

                message = await ctx.send(embed=embeds[0])
                await message.add_reaction("⬅️")
                await message.add_reaction("❌")
                await message.add_reaction("➡️")
                
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️", "❌"] and reaction.message.id == message.id

                i = 0
                while True:
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
                        if str(reaction.emoji) == "➡️":
                            i += 1
                            if i >= len(embeds):
                                i = 0
                            await message.edit(embed=embeds[i])
                        elif str(reaction.emoji) == "⬅️":
                            i -= 1
                            if i < 0:
                                i = len(embeds) - 1
                            await message.edit(embed=embeds[i])
                        elif str(reaction.emoji) == "❌":
                            await message.delete()
                            break
                        await message.remove_reaction(reaction, user)
                    except asyncio.TimeoutError:
                        i += 1
                        if i >= len(embeds):
                            i = 0
                        await message.edit(embed=embeds[i])
            except aiohttp.ClientError as e:
                await ctx.send(f"An error occurred while trying to fetch data: {str(e)}")
            except Exception as e:
                await ctx.send(f"An unexpected error occurred: {str(e)}")
