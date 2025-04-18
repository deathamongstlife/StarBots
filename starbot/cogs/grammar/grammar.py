from Star-Utils import Cog, CogsUtils
"""
MIT License

Copyright (c) 2018-Present NeuroAssassin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import aiohttp
from starbot.core import commands

from .converters import Gargs

URL = "http://api.datamuse.com/words"


class Grammar(Cog):
    """Get words related to the specified arguments"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def red_delete_data_for_user(self, **kwargs):
        """This cog does not store user data"""
        return

    @commands.command()
    async def grammar(self, ctx, *, args: Gargs):
        """Get words related to the passed arguments.

        Arguments must have `--` before them.
           `meaning-like`/`ml`: Get words that mean close to what the passed word means.
           `spelled-like`/`sp`: Get words that are spelled like the passed word.
           `sounds-like`/`sl`: Get words that sound like the passed word.
           `rhymes-with`/`rw`: Get words that rhyme with the passed word.
           `adjectives-for`/`af`: Get adjectives for the passed noun.
           `nouns-for`/`nf`: Get nouns for the passed adjective.
           `comes-before`/`cb`: Get words that usually come before the passed word.
           `comes-after`/`ca`: Get words that usually come after the passed word.
           `topics`: Get words that are related to the passed topic.  Max 5 words.
           `synonyms-for`/`sf`: Get synonyms for the passed word.
           `antonyms-for`/`anf`: Get antonyms for the passed word.
           `kind-of`/`ko`: Get the kind of what the passed word is (Computer -> Machine).
           `more-specific-than`/`mst`: Get more specific nouns for the passed word (Ex: Machine -> Computer).
           `homophones`/`h`: Get homophones of the passed word."""
        data = args
        async with self.session.get(URL, params=data) as r:
            if r.status != 200:
                return await ctx.send(f"Invalid status code: {r.status}")
            text = await r.json()
        sending = "Here are the top 10 words that came close to your filters:\n```\n"
        for x in text:
            sending += x["word"] + "\n"
        sending += "```"
        await ctx.send(sending)
