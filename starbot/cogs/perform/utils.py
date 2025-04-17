import contextlib
from typing import Optional, Union, List

import aiohttp
import discord
from aiohttp.client_exceptions import ContentTypeError
from starbot.core import commands
from starbot.core.utils.chat_formatting import box
from tabulate import tabulate


async def api_call(call_uri: str, returnObj: Optional[bool] = False):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{call_uri}") as response:
            response = await response.json()
            if returnObj is False:
                return response["response"]
            elif returnObj is True:
                return response
    await session.close()


async def has_webhook_perms(ctx: commands.Context) -> bool:
    if isinstance(ctx.channel, discord.DMChannel):
        return True
    if ctx.channel.guild is None:
        return False
    perm = ctx.channel.permissions_for(ctx.channel.guild.me).manage_webhooks
    return perm is True


async def has_embed_perms(ctx: commands.Context) -> bool:
    # Allow embeds in DMs and group chats
    if isinstance(ctx.channel, (discord.DMChannel, discord.GroupChannel)):
        return True
    # Check permissions in server channels
    if ctx.guild is not None:
        perm = ctx.channel.permissions_for(ctx.guild.me).embed_links
        return perm is True
    return False  # Default to False if the context is unexpected


async def send_embed(
    self,
    ctx: commands.Context,
    embed: discord.Embed,
    users: Optional[List[discord.Member]] = None,
):
    # Handle DMs and group chats
    if isinstance(ctx.channel, (discord.DMChannel, discord.GroupChannel)):
        if users:
            mentions = " ".join(user.mention for user in users)
            await ctx.send(embed=embed, content=mentions)
        else:
            await ctx.send(embed=embed)
        return

    # Handle server channels
    if await has_webhook_perms(ctx):
        try:
            if users:
                await print_it(self, ctx, embed, users)
            else:
                await print_it(self, ctx, embed)
        except discord.Forbidden:
            if not await has_embed_perms(ctx):
                return await ctx.send(
                    "I need the `Embed Links` permission to send embeds in this channel."
                )
            if users:
                mentions = " ".join(user.mention for user in users)
                await ctx.reply(embed=embed, content=mentions, mention_author=False)
            else:
                await ctx.reply(embed=embed, mention_author=False)
    elif not await has_embed_perms(ctx):
        return await ctx.send(
            "I need the `Embed Links` permission to send embeds in this channel."
        )
    elif users:
        mentions = " ".join(user.mention for user in users)
        await ctx.reply(embed=embed, content=mentions, mention_author=False)
    else:
        await ctx.reply(embed=embed, mention_author=False)


async def kawaiiembed(
    self, ctx: commands.Context, action: str, endpoint: str, users=None
) -> Union[discord.Embed, str]:
    api_key = (await self.bot.get_shared_api_tokens("perform")).get("api_key")
    if not api_key:
        return "Set an API token before using this command. If you are the bot owner, then use `[p]performapi` to see how to add the API."

    if users is None:
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** {action}",
            color=discord.Colour.random(),
        )
    else:
        mentions = " ".join(f"**{user.mention}**" for user in users)
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** {action} {mentions}!",
            color=discord.Colour.random(),
        )

    embed.set_author(
        name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar
    )
    try:
        url = await api_call(f"https://kawaii.red/api/gif/{endpoint}/token={api_key}")
    except (ContentTypeError, KeyError):
        return "The API returned an error. Please try again later."
    embed.set_image(url=url)

    return embed


async def add_footer(
    self, ctx: commands.Context, embed: discord.Embed, used: int, word1: str, **kwargs
):
    if not await self.config.footer():
        return
    target = kwargs.get("target")
    word2 = kwargs.get("word2")
    users = kwargs.get("users")
    if (target is not None) and (word2 is not None) and (users is not None):
        mentions = ", ".join(user.display_name for user in users)
        embed.set_footer(
            text=f"{ctx.author.display_name}'s total {word1}: {used + 1} | {ctx.author.display_name} has {word2} {mentions} {target + 1} times"
        )
    else:
        embed.set_footer(text=f"{ctx.author.display_name}'s total {word1}: {used + 1}")


async def get_hook(self, ctx: commands.Context):
    if isinstance(ctx.channel, discord.Thread):
        channel = ctx.channel.parent
    else:
        channel = ctx.channel
    try:
        if channel.id not in self.cache:
            for i in await channel.webhooks():
                if i.user.id == self.bot.user.id:
                    hook = i
                    self.cache[channel.id] = hook
                    break
            else:
                hook = await channel.create_webhook(
                    name=f"action_webhook_{str(channel.id)}"
                )

        else:
            hook = self.cache[channel.id]
    except discord.NotFound:  # Probably user deleted the hook
        hook = await channel.create_webhook(name=f"action_webhook_{str(channel.id)}")
    return hook


async def print_it(
    self,
    ctx: commands.Context,
    embed: discord.Embed,
    users: Optional[List[discord.User]] = None,
    retried: bool = False,
):
    hook = await get_hook(self, ctx)
    try:
        if users:
            mentions = " ".join(user.mention for user in users)
            await hook.send(
                username=ctx.message.author.display_name,
                avatar_url=ctx.message.author.display_avatar,
                embed=embed,
                content=mentions,
                thread=(
                    ctx.channel
                    if isinstance(ctx.channel, discord.Thread)
                    else discord.utils.MISSING
                ),
            )
        else:
            await hook.send(
                username=ctx.message.author.display_name,
                avatar_url=ctx.message.author.display_avatar,
                embed=embed,
                thread=(
                    ctx.channel
                    if isinstance(ctx.channel, discord.Thread)
                    else discord.utils.MISSING
                ),
            )
    except discord.NotFound:
        if retried:  # This is an edge case, just a hack to prevent infinite loops
            return await ctx.send("I can't find the webhook, sorry.")
        self.cache.pop(
            ctx.channel.parent.id
            if isinstance(ctx.channel, discord.Thread)
            else ctx.channel.id
        )
        await print_it(self, ctx, embed, users, retried=True)


async def rstats_embed(
    self,
    ctx: commands.Context,
    action: str,
    user: discord.User,
):
    custom = await self.config.custom("Target").all()
    em = discord.Embed(
        title=f"{user.name}'s {action} stats", color=await ctx.embed_color()
    )
    em.set_author(name=user, icon_url=user.display_avatar)
    em.set_footer(text=f"Requested by {ctx.author}")

    user_cache = {}
    sent = {}
    for who, to_who_d in custom.items():
        for to_who, _ in to_who_d.items():
            who_id = int(who)
            to_who_id = int(to_who)
            with contextlib.suppress(KeyError, discord.NotFound):
                if who_id != user.id:
                    continue
                if (
                    custom_value := custom.get(who, {})
                    .get(to_who, {})
                    .get(f"{action}_r")
                ):
                    sent[to_who] = custom_value
    sent = sorted(sent.items(), key=lambda x: x[1], reverse=True)
    rsent = sum(v for _, v in sent)
    sent = [
        (
            [user_cache.get(int(k), await self.bot.get_or_fetch_user(int(k))), v]
            if (user_cache.get(int(k), await self.bot.get_or_fetch_user(int(k))))
            else ["Deleted User", v]
        )
        for k, v in sent[:10]
    ]
    sent = tabulate(sent, tablefmt="fancy", headers=["User", "Amount"])

    em.add_field(
        name=f"Sent {action}s: {rsent}",
        value=(
            box(sent, lang="sml")
            if rsent != 0
            else f"You haven't sent any {action} yet."
        ),
        inline=False,
    )

    received = {}
    for who, to_who_d in custom.items():
        for to_who, _ in to_who_d.items():
            who_id = int(who)
            to_who_id = int(to_who)
            with contextlib.suppress(KeyError, discord.NotFound):
                if to_who_id != user.id:
                    continue
                if (
                    custom_value := custom.get(who, {})
                    .get(to_who, {})
                    .get(f"{action}_r")
                ):
                    received[who] = custom_value
    received = sorted(received.items(), key=lambda x: x[1], reverse=True)
    rcount = sum(v for _, v in received)
    received = [
        (
            [user_cache.get(int(k), await self.bot.get_or_fetch_user(int(k))), v]
            if (user_cache.get(int(k), await self.bot.get_or_fetch_user(int(k))))
            else ["Deleted User", v]
        )
        for k, v in received[:10]
    ]
    received = tabulate(received, tablefmt="fancy", headers=["User", "Amount"])

    em.add_field(
        name=f"Received {action}s: {rcount}",
        value=(
            box(received, lang="sml")
            if rcount != 0
            else f"You haven't received any {action} yet."
        ),
        inline=False,
    )

    return em
