import asyncio
from pathlib import Path

import discord
import yaml
from discord.ext import commands
from pydactyl import PterodactylClient

from utils.functions import get_modules
from utils.objects import BotConfig, Object


class TreasureMiner(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=">",
            description="A discord bot to monitor current Devilfruit Circulation from the MineMineNoMi mod",
            status=discord.Status.dnd,
            activity=discord.Game(f"Starting Up..."),
            intents=discord.Intents.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )
        self.path = Path(__file__).parent
        self.modules_path = self.path.joinpath("modules")
        self.remove_command("help")
        self.load_config()

    def load_config(self):
        # Load bot's configurations
        config = yaml.safe_load(open("config.yaml"))
        self.config = BotConfig(**config)

    async def setup_constants(self):
        # Setup constants for the bot to use
        self._last_exception = None
        self.constants = Object()
        self.GOLDEN_COLOR = 0xFFD700
        # self.constants.ptero_client = PterodactylClient(
        #     self.config.ptero_server, self.config.ptero_api_key
        # )

    async def load_modules(self):
        # Loads bot's modules
        for module in get_modules(self.modules_path):
            await self.load_extension(module.spec)
            print(f"Loaded module {module.name}")

    async def setup_hook(self):
        # Things to do when the bot is ready to go
        await self.setup_constants()
        await self.load_modules()
        asyncio.create_task(self.change_status())

    async def change_status(self):
        await self.wait_until_ready()
        await self.change_presence(status=discord.Status.online)

    def run(self, **kwargs):
        # Run the bot
        super().run(self.config.discord_api_key, **kwargs)

    async def on_message(self, message):
        if message.author.id not in self.bot.config.bot_owners:
            return
        await self.process_commands(message)


if __name__ == "__main__":
    try:
        bot = TreasureMiner()
        bot.run(reconnect=True)
    except KeyboardInterrupt:
        print("Shutting down bot...")
