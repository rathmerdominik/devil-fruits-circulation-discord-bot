import asyncio
from datetime import datetime
from json import load
from pathlib import Path

from discord import Embed
from discord.errors import NotFound
from discord.ext import commands, tasks
from utils.functions import (
    chunks,
    convert_nbt_to_dict,
    list_devil_fruits,
    list_eaten_fruits,
    list_inventory_fruits,
    load_nbt,
    yaml_load,
)
from utils.objects import DFCircConfig


class devil_fruit_circulation(commands.Cog):
    """A module for Devil Fruit Circulation."""

    def __init__(self, bot):
        self.bot = bot
        self.config = DFCircConfig(**yaml_load(Path(__file__).parent))
        self.fruits = list(
            list_devil_fruits(load(open("resources/fruits_config/fruits.json")))
        )
        self.nbt_path = "{0}/data/mineminenomi.dat".format(self.bot.config.world_name)

    async def cog_load(self):
        asyncio.create_task(self.startup())

    async def startup(self):
        """Sets up constants and starts the module's."""
        await self.bot.wait_until_ready()
        self.channel = self.bot.get_channel(self.config.channel)
        self.golden_box_emoji = self.bot.get_emoji(self.config.golden_box)
        self.iron_box_emoji = self.bot.get_emoji(self.config.iron_box)
        self.wooden_box_emoji = self.bot.get_emoji(self.config.wooden_box)
        self.update_df_circulation.start()

    async def cog_unload(self):
        self.update_df_circulation.cancel()

    async def get_editable_message(self):
        """Gets a message that can be edited from the specified channel."""
        if self.channel is None:
            raise Exception(
                "\nUnable to start updating devil fruit circulation, no channel found with ID {0}\n"
                "Make sure to edit '\modules\devil_fruit_circulation\config.yaml'".format(
                    self.config.channel
                )
            )
        async for m in self.channel.history(limit=50):
            if (
                m.author == self.bot.user
                and m.embeds
                and m.embeds[0].description == "__**All available Devil Fruits**__"
            ):
                return m
        return None

    @tasks.loop(minutes=5)
    async def update_df_circulation(self):
        """Updates the devil fruit circulation every 5 minutes."""
        nbt_data = await load_nbt(self.bot.config, self.nbt_path)
        if nbt_data is None:
            print("Unable to read NBT data, was it loaded?")
            return
        fruit_data = convert_nbt_to_dict(nbt_data)
        update = self.build_formatted_message(fruit_data)
        if not hasattr(self, "df_message"):
            try:
                self.df_message = await self.get_editable_message()
            except Exception as e:
                print(e)
                return
        if self.df_message is None:
            self.df_message = await self.channel.send(embed=update)
        else:
            try:
                await self.df_message.edit(embed=update)
            except NotFound:
                self.df_message = await self.channel.send(embed=update)
        await self.df_message.edit(embed=update)
        print(
            f"Updated Devil Fruit Circulation {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def build_formatted_message(self, fruit_data: dict) -> Embed:
        """Builds the formatted message to be sent to the channel."""
        embed: Embed = Embed(
            title="{g}{i}{w}Current Devilfruit Circulation{w}{i}{g}".format(
                g=self.golden_box_emoji,
                i=self.iron_box_emoji,
                w=self.wooden_box_emoji,
            ),
            description="__**All available Devil Fruits**__",
            color=self.bot.GOLDEN_COLOR,
        )
        embed.set_footer(text="Circulation is updated every 5 minutes")
        eaten_fruits = list_eaten_fruits(self.fruits, fruit_data)
        inventory_fruits = list_inventory_fruits(self.fruits, fruit_data)
        unavailable_fruits = eaten_fruits + inventory_fruits
        order = ["golden_box", "iron_box", "wooden_box"]
        available_fruits = [
            f"{getattr(self, f'{fruit.rarity}_emoji')}{fruit.format_name}"
            for fruit in sorted(self.fruits, key=lambda x: order.index(x.rarity))
            if fruit not in unavailable_fruits
        ]
        available_fruits_fields = chunks(available_fruits, 8)
        for fruits in available_fruits_fields:
            embed.add_field(
                name="\u200b",
                value="\n".join(fruits),
            )
        return embed


async def setup(bot):
    await bot.add_cog(devil_fruit_circulation(bot))
