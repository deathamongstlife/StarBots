# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from abc import ABC, ABCMeta
from typing import Optional, Union

import discord
from discord.ext.commands.cog import CogMeta
from starbot.core import commands, Config
from starbot.core.bot import Red


class ABMixin(ABC):
    def __init__(self, *_args):
        self.bot: Red
        self.config: Config

    def _get_user(
        self, ctx: commands.Context, member_id: str
    ) -> Optional[Union[discord.Member, discord.User]]:
        ...


class CompositeMetaclass(CogMeta, ABCMeta):
    ...
