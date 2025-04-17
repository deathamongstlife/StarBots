import discord
import logging

from typing import TYPE_CHECKING, Optional, TypeVar, Type, List
from discord.ui import Select, View, button
from starbot.core.utils.chat_formatting import text_to_file

from instantcmd.core import CodeSnippet

if TYPE_CHECKING:
    from starbot.core.bot import Red
    from .instantcmd import InstantCommands

log = logging.getLogger("red.laggron.instantcmd.components")
T = TypeVar("T", bound=CodeSnippet)


def char_limit(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[: limit - 3] + "..."
    else:
        return text


class OwnerOnlyView(View):
    """
    A view where only bot owners are allowed to interact.
    """

    def __init__(self, bot: "Red", *, timeout: Optional[float] = 180):
        self.bot = bot
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await self.bot.is_owner(interaction.user)


class CodeSnippetView(OwnerOnlyView):
    """
    List of buttons for a single code snippet.
    """

    def __init__(
        self, bot: "Red", cog: "InstantCommands", interaction: discord.Interaction, code_snippet: T
    ):
        self.cog = cog
        self.code_snippet = code_snippet
        self.og_interaction = interaction
        super().__init__(bot)
        self.set_activate_button()

    async def edit(self):
        # refresh activate/deactivate button
        await self.og_interaction.followup.edit_message("@original", view=self)

    def set_activate_button(self):
        if self.code_snippet.enabled:
            self.activate_deactivate.style = discord.ButtonStyle.secondary
            self.activate_deactivate.label = "Disable"
            self.activate_deactivate.emoji = "\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}"
        else:
            self.activate_deactivate.style = discord.ButtonStyle.success
            self.activate_deactivate.label = "Enable"
            self.activate_deactivate.emoji = "\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}"

    @button()
    async def activate_deactivate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.code_snippet.enabled:
            log.info(f"Code snippet {self.code_snippet} disabled.")
            self.code_snippet.enabled = False
            await self.code_snippet.save()
            try:
                self.code_snippet.unregister()
            except Exception:
                log.error(
                    f"Failed to unregister {self.code_snippet} when deactivation requested",
                    exc_info=True,
                )
                await interaction.response.send_message(
                    "An error occured when trying to unregister this object, you can check for "
                    "details in your logs.\n"
                    "It is still deactivated and will not be loaded on next cog load."
                )
            else:
                self.set_activate_button()
                await interaction.response.send_message(
                    "The object was successfully unregistered and will not be loaded again."
                )
                await self.edit()
        else:
            try:
                self.code_snippet.register()
            except Exception:
                log.error(
                    f"Failed to register {self.code_snippet} when activation requested",
                    exc_info=True,
                )
                await interaction.response.send_message(
                    "An error occured when trying to register this object, you can check for "
                    "details in your logs.\n"
                    "It is still deactivated, you can try to activate it again."
                )
            else:
                log.info(f"Code snippet {self.code_snippet} enabled.")
                self.code_snippet.enabled = True
                await self.code_snippet.save()
                self.set_activate_button()
                await interaction.response.send_message(
                    "The object was successfully registered and will be loaded on cog load."
                )
                await self.edit()

    @button(style=discord.ButtonStyle.danger, label="Delete", emoji="\N{OCTAGONAL SIGN}")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.code_snippet.delete()
        try:
            self.cog.code_snippets.remove(self.code_snippet)
        except ValueError:
            pass
        try:
            self.code_snippet.unregister()
        except Exception:
            log.error(
                f"Failed to unregister {self.code_snippet} when deletion requested",
                exc_info=True,
            )
            await interaction.response.send_message(
                "An error occured when trying to unregister this object, you can check for "
                "details in your logs.\n"
                "It was still removed and will not be loaded on next cog load."
            )
        else:
            await interaction.response.send_message("Object successfully removed.")
        finally:
            self.stop()


class CodeSnippetsList(Select):
    """
    A list of items for a specific type of code snippet.
    """

    def __init__(self, bot: "Red", cog: "InstantCommands", type: Type[T], code_snippets: List[T]):
        self.bot = bot
        self.cog = cog
        self.snippet_type = type
        self.code_snippets = code_snippets

        placeholder = f"List of {type.name} objects"
        objects: List[discord.SelectOption] = []

        # TODO: Support more than 25 items!
        for i, code_snippet in enumerate(code_snippets[:25]):
            lines = code_snippet.source.count("\n") + 1
            value = f"{lines} lines of code"
            if code_snippet.verbose_name != str(code_snippet):
                value += f" • {code_snippet.description}"
            objects.append(
                discord.SelectOption(
                    label=char_limit(str(code_snippet), 25),
                    description=char_limit(value, 50),
                    value=str(i),
                )
            )
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=objects)

    async def callback(self, interaction: discord.Interaction):
        selected = self.code_snippets[int(self.values[0])]
        message = f"__{selected.name} `{selected}`__"
        if selected.verbose_name != str(selected):
            message += f" ({selected.description})"
        await interaction.response.send_message(
            message,
            view=CodeSnippetView(self.bot, self.cog, interaction, selected),
            file=text_to_file(selected.source, filename=f"{selected}.py"),
        )
