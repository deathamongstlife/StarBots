import asyncio
import functools
import logging
import os
from io import BytesIO
from typing import Optional
from Star-Utils import Cog, CogsUtils

import aiohttp
import discord
from gsbl.stick_bug import StickBug
from PIL import Image
from starbot.core import commands
from starbot.core.data_manager import cog_data_path

from .converters import ImageFinder

log = logging.getLogger("red.flare.stick")


class StickBugged(Cog):
        

    def __init__(self, bot) -> None:
        self.bot = bot
        self._stickbug = StickBug()

    def blocking(self, io, id):
        io = Image.open(io)
        self._stickbug.image = io

        self._stickbug.video_resolution = max(min(1280, io.width), 128), max(
            min(720, io.height), 72
        )
        self._stickbug.lsd_scale = 0.35
        video = self._stickbug.video
        video.write_videofile(
            str(cog_data_path(self)) + f"/{id}stick2.mp4",
            threads=1,
            preset="superfast",
            verbose=False,
            logger=None,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(cog_data_path(self) / f"{id}stick3.mp4"),
        )
        video.close()
        return

    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.command(aliases=["stickbug", "stickbugged"])
    async def stick(self, ctx, images: Optional[ImageFinder]):
        """get stick bugged lol"""
        if images is None:
            images = await ImageFinder().search_for_images(ctx)
        if not images:
            return await ctx.send_help()
        image = images
        async with ctx.typing():
            io = BytesIO()
            if isinstance(image, discord.Asset):
                await image.save(io, seek_begin=True)
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(image)) as resp:
                        if resp.status != 200:
                            return await ctx.send("The picture returned an unknown status code.")
                        io.write(await resp.read())
                        io.seek(0)

            # Resize the image if it's smaller than 512 pixels
            img = Image.open(io)
            if img.width < 512 or img.height < 512:
                img = img.resize((512, 512))
                io = BytesIO()
                img.save(io, format='PNG')
                io.seek(0)
            
            await asyncio.sleep(0.2)
            fake_task = functools.partial(self.blocking, io=io, id=ctx.message.id)
            task = self.bot.loop.run_in_executor(None, fake_task)
            try:
                video_file = await asyncio.wait_for(task, timeout=300)
            except asyncio.TimeoutError as e:
                log.error("Timeout creating stickbug video", exc_info=e)
                return await ctx.send("Timeout creating stickbug video.")
            except Exception as e:
                log.exception("Error sending stick bugged video")
                error_message = f"An error occurred during the creation of the stick bugged video: {str(e)} \n Try mentioning someone when using the command?"
                return await ctx.send(error_message)

            fp = cog_data_path(self) / f"{ctx.message.id}stick2.mp4"
            
            file = discord.File(str(fp), filename="stick2.mp4")
            try:
                await ctx.send(files=[file])
            except Exception as e:
                log.error("Error sending stick bugged video", exc_info=e)
            try:
                os.remove(fp)
            except Exception as e:
                log.error("Error deleting stick bugged video", exc_info=e)
