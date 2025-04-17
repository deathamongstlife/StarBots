from starbot.core import commands
from starbot.core.i18n import Translator, cog_i18n

from pylav.events.player import PlayerDisconnectedEvent, PlayerStoppedEvent
from pylav.events.track import TrackEndEvent, TrackResumedEvent, TrackStartEvent
from pylav.logging import getLogger
from pylav.players.player import Player
from pylav.type_hints.bot import DISCORD_BOT_TYPE

log = getLogger("PyLav.3rdpt.karlo-cogs.pylavchannelstatus")
_ = Translator("PyLavChannelStatus", __file__)


@cog_i18n(_)
class PyLavChannelStatus(commands.Cog):
    def __init__(self, bot: DISCORD_BOT_TYPE):
        self.bot: DISCORD_BOT_TYPE = bot

    async def set_channel_status(self, event: TrackStartEvent | TrackResumedEvent):
        player: Player = event.player
        channel = player.channel
        track_name = await event.track.get_track_display_name(
            max_length=500,
            author=True,
            unformatted=True,
            escape=False,
        )
        await channel._edit(
            options={"status": track_name},
            reason=_("[PyLavChannelStatus] Setting channel status to new track"),
        )

    async def remove_channel_status(
        self, event: TrackEndEvent | PlayerDisconnectedEvent | PlayerStoppedEvent
    ):
        player: Player = event.player
        channel = player.channel
        if player.current:
            return
        await channel._edit(
            options={"status": None},
            reason=_("[PyLavChannelStatus] Removing channel status"),
        )

    @commands.Cog.listener()
    async def on_pylav_track_start_event(self, event: TrackStartEvent):
        await self.set_channel_status(event)

    @commands.Cog.listener()
    async def on_pylav_track_resumed_event(self, event: TrackResumedEvent):
        await self.set_channel_status(event)

    @commands.Cog.listener()
    async def on_pylav_track_end_event(self, event: TrackEndEvent):
        await self.remove_channel_status(event)

    @commands.Cog.listener()
    async def on_pylav_player_disconnected_event(self, event: PlayerDisconnectedEvent):
        await self.remove_channel_status(event)

    @commands.Cog.listener()
    async def on_pylav_player_stopped_event(self, event: PlayerStoppedEvent):
        await self.remove_channel_status(event)
