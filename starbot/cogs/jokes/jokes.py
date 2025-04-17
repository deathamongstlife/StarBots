from jokeapi import Jokes as jokes
from starbot.core import commands
from starbot.core.bot import Red
from Star-Utils import Cog, CogsUtils


class Jokes(Cog):
    """Get some jokes from the Joke API."""

    def __init__(self, bot: Red):
        self.bot = bot

    async def red_delete_data_for_user(self):
        """Nothing to delete."""
        return

    @commands.command(name="joke")
    async def joke(self, ctx):
        """Get a random joke."""
        j = await jokes()
        joke = await j.get_joke(
            response_format="txt",
            blacklist=["nsfw", "religious", "political", "racist", "sexist"],
        )
        await ctx.send(joke)

    @commands.command(name="darkjoke")
    async def darkjoke(self, ctx):
        """Get a random dark joke."""
        j = await jokes()
        joke = await j.get_joke(response_format="txt", category=["dark"])
        await ctx.send(joke)

    @commands.command(name="pun")
    async def pun(self, ctx):
        """Get a random pun."""
        j = await jokes()
        joke = await j.get_joke(response_format="txt", category=["pun"])
        await ctx.send(joke)

    @commands.command(name="devjoke")
    async def devjoke(self, ctx):
        """Get a random dev joke."""
        j = await jokes()
        joke = await j.get_joke(response_format="txt", category=["programming"])
        await ctx.send(joke)

    @commands.command(name="twopart", aliases=["2part"])
    async def twopart(self, ctx):
        """Get a random 2 part joke."""
        j = await jokes()
        joke = await j.get_joke(
            response_format="txt",
            joke_type="twopart",
            blacklist=["nsfw", "religious", "political", "racist", "sexist"],
        )
        await ctx.send(joke)

    @commands.command(name="onepart", aliases=["1part"])
    async def onepart(self, ctx):
        """Get a random 1 part joke."""
        j = await jokes()
        joke = await j.get_joke(
            response_format="txt",
            joke_type="single",
            blacklist=["nsfw", "religious", "political", "racist", "sexist"],
        )
        await ctx.send(joke)

    @commands.command(name="jokesearch")
    async def jokesearch(self, ctx, query: str):
        """Search for a random joke with a specific query."""
        j = await jokes()
        joke = await j.get_joke(
            response_format="txt",
            search_string=query,
            blacklist=["nsfw", "religious", "political", "racist", "sexist"],
        )

        await ctx.send(joke)

    @commands.command(name="multijoke")
    async def multijoke(self, ctx, number: int):
        """Get multiple random joke(s).

        10 is the max number of jokes you can get at once.

        """
        if number < 10:
            j = await jokes()
            joke = await j.get_joke(
                response_format="txt",
                amount=number,
                blacklist=["nsfw", "religious", "political", "racist", "sexist"],
            )

            await ctx.send(joke)
        else:
            await ctx.send("10 is the maximum number of jokes you can get at once.")
