from Star-Utils import Cog, CogsUtils
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord

from starbot.core import commands, checks
from starbot.core.utils.chat_formatting import pagify, escape
from starbot.core.utils.menus import menu, DEFAULT_CONTROLS
from Star-Utils import Cog
import datetime

class Freshmeat(Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logs = CogsUtils.get_logger("FreshMeat")

    async def red_get_data_for_user(self, **kwargs):
        return {}

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @checks.admin_or_permissions(kick_members=True)
    async def freshmeat(self, ctx, hours: int = 24):
        """Show the members who joined in the specified timeframe

        `hours`: A number of hours to check for new members, must be above 0"""
        if hours < 1:
            return await ctx.send("Consider putting hours above 0. Since that helps with searching for members. ;)")
        elif hours > 300:
            return await ctx.send("Please use something less then 300 hours.")

        member_list = []
        for member in ctx.guild.members:
            if (
                member.joined_at is not None
                and member.joined_at > (ctx.message.created_at - datetime.timedelta(hours=hours))
            ):
                member_list.append([member.display_name, member.id, member.joined_at])

        member_list.sort(key=lambda member: member[2], reverse=True)
        member_string = ""
        for member in member_list:
            member_string += f"\n{member[0]} ({member[1]})"

        pages = []
        for page in pagify(escape(member_string, formatting=True), page_length=1000):
            embed = discord.Embed(description=page)
            embed.set_author(
                name=f"{ctx.author.display_name}'s freshmeat of the day.",
                icon_url=ctx.author.display_avatar,
            )
            pages.append(embed)

        page_counter = 1
        for page in pages:
            page.set_footer(text=f"Page {page_counter} out of {len(pages)}")
            page_counter += 1

        if not pages:
            return await ctx.send("No new members joined in specified timeframe.")

        await menu(
            ctx,
            pages=pages,
            controls=DEFAULT_CONTROLS,
            message=None,
            page=0,
            timeout=90
        )
