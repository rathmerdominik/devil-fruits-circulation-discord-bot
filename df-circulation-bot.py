import pydactyl
from pydactyl import PterodactylClient
from requests import HTTPError
import yaml
from yaml.loader import SafeLoader
import os
import json
import urllib
import nbt
import io
import discord
from discord import Message, TextChannel, Embed
from discord.ext import tasks
import datetime as dt
from time import sleep


GOLDEN_COLOR = 0xFFD700
discord_client = discord.Client()


@tasks.loop(minutes=5)
async def update_df_circulation():
    await discord_client.wait_until_ready()
    await stall_until_nbt_data_exists.start()
    await discord_client.message.edit(
        embed=await build_formatted_message(
            discord_client.config, discord_client.nbt_data
        )
    )
    print(
        f"Updated Devil Fruit Circulation {dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S')}"
    )


@tasks.loop(seconds=10)
async def stall_until_nbt_data_exists() -> nbt:
    await discord_client.wait_until_ready()

    nbt_data: nbt = {}
    try:
        discord_client.nbt_data = await get_nbt_data(
            discord_client.ptero_client,
            discord_client.mine_mine_nbt_path,
            discord_client.server_id,
        )
        stall_until_nbt_data_exists.stop()
        return

    except HTTPError as e:
        print("mineminenomi.dat not existing. Wait for a player to choose a race")


@discord_client.event
async def on_ready():
    with open("config.yaml") as f:
        config: dict = yaml.load(f, Loader=SafeLoader)

    ptero_client: PterodactylClient = PterodactylClient(
        config["ptero_server"], config["ptero_api_key"]
    )

    server_config: dict = await get_server_config(ptero_client)
    server_id: str = server_config["server_id"]

    if "message_id" in server_config:
        message_id: int = server_config["message_id"]
    else:
        message_id: None = None

    discord_client.mine_mine_nbt_path: str = "{0}/data/mineminenomi.dat".format(
        config["world_name"]
    )
    discord_client.server_id: str = server_id
    discord_client.ptero_client: PterodactylClient = ptero_client
    await stall_until_nbt_data_exists.start()

    nbt_data: nbt = discord_client.nbt_data
    channel: TextChannel = discord_client.get_channel(config["discord_channel"])
    message: Message = await get_editable_message(channel, nbt_data, config, message_id)

    discord_client.message = message
    discord_client.config = config

    update_df_circulation.start()


async def get_editable_message(
    channel: TextChannel, nbt_data: nbt, config: dict, message_id: int
) -> int:
    try:
        if not message_id:
            embed: Embed = await build_formatted_message(config, nbt_data)
            message: Message = await channel.send(embed=embed)

            with open("server.json", "r+") as f:
                config = json.load(f)
                config["message_id"] = message.id
                f.seek(0)
                json.dump(config, f)
                f.truncate()
        else:
            message: Message = await channel.fetch_message(message_id)
    except NotFound:
        await get_editable_message(channel, nbt_data, config, None)
    return message


async def build_formatted_message(config: dict, nbt_data: nbt) -> Embed:
    taken_fruits: list = (
        await get_fruits_eaten(nbt_data)
        + await get_fruits_in_inventory(nbt_data)
        + await get_fruits_in_world(nbt_data)
    )
    all_fruits: list = await get_all_fruits()
    fruits_available: list = list(set(all_fruits) - set(taken_fruits))
    mapped_fruits: list = await get_mapped_devil_fruits(fruits_available)

    golden_box = discord_client.get_emoji(1006270786287443978)
    iron_box = discord_client.get_emoji(1006326985934516285)
    wooden_box = discord_client.get_emoji(1006327000270655579)

    embed: Embed = discord.Embed(
        title="{golden}{iron}{wooden}Current Devilfruit Circulation{wooden}{iron}{golden}".format(
            golden=golden_box, iron=iron_box, wooden=wooden_box
        ),
        description="__**All available Devil Fruits**__",
        color=GOLDEN_COLOR,
        timestamp=dt.datetime.utcnow()
    )
    embed.set_footer(text="Circulation is updated every 5 minutes | Last updated")

    embed_formatted_fruits: list = []

    golden_arr: list = []
    iron_arr: list = []
    wooden_arr: list = []

    for fruit_mapped in mapped_fruits:
        for fruit_available in fruits_available:
            if fruit_available in list(fruit_mapped.keys()):
                if fruit_mapped[fruit_available]["rarity"] == "golden_box":
                    golden_arr.append(fruit_mapped)
                elif fruit_mapped[fruit_available]["rarity"] == "iron_box":
                    iron_arr.append(fruit_mapped)
                elif fruit_mapped[fruit_available]["rarity"] == "wooden_box":
                    wooden_arr.append(fruit_mapped)
    mapped_fruits = golden_arr + iron_arr + wooden_arr

    # TODO may god help us. This definitly has to be refactored. No idea how
    for fruit_mapped in mapped_fruits:
        for fruit_available in fruits_available:
            if fruit_available in list(fruit_mapped.keys()):
                if fruit_mapped[fruit_available]["rarity"] == "golden_box":
                    embed_formatted_fruits.append(
                        "{rarity}{format_name}".format(
                            rarity=golden_box,
                            format_name=fruit_mapped[fruit_available]["format_name"],
                        )
                    )
                elif fruit_mapped[fruit_available]["rarity"] == "iron_box":
                    embed_formatted_fruits.append(
                        "{rarity}{format_name}".format(
                            rarity=iron_box,
                            format_name=fruit_mapped[fruit_available]["format_name"],
                        )
                    )
                elif fruit_mapped[fruit_available]["rarity"] == "wooden_box":
                    embed_formatted_fruits.append(
                        "{rarity}{format_name}".format(
                            rarity=wooden_box,
                            format_name=fruit_mapped[fruit_available]["format_name"],
                        )
                    )

    formatted_fruits_to_add: list = []

    for idx, formatted_fruit in enumerate(embed_formatted_fruits):
        if idx != 0 and idx % 7 == 0:
            embed.add_field(
                name=" \u200b", value="\n".join(formatted_fruits_to_add), inline=True
            )
            formatted_fruits_to_add = []
        else:
            formatted_fruits_to_add.append(formatted_fruit)
    if len(formatted_fruits_to_add) != 0:
        embed.add_field(
            name=" \u200b", value="\n".join(formatted_fruits_to_add), inline=True
        )

    return embed


async def get_mapped_devil_fruits(devil_fruits: list) -> list:
    fruit_map: dict = {}
    mapped_fruits: list = []

    with open("resources/fruits_config/fruits.json", "r") as f:
        fruit_map = json.load(f)
    golden_box = [value for elem in fruit_map["golden_box"] for value in elem.values()]
    iron_box = [value for elem in fruit_map["iron_box"] for value in elem.values()]
    wooden_box = [value for elem in fruit_map["wooden_box"] for value in elem.values()]

    # TODO Wtf did i even do here. Help
    for devil_fruit in devil_fruits:
        for golden_box in fruit_map["golden_box"]:
            if devil_fruit in list(golden_box.keys()):
                mapped_fruits.append(
                    {
                        devil_fruit: {
                            "name": golden_box[devil_fruit]["name"],
                            "format_name": golden_box[devil_fruit]["format_name"],
                            "rarity": "golden_box",
                        }
                    }
                )
        for iron_box in fruit_map["iron_box"]:
            if devil_fruit in list(iron_box.keys()):
                mapped_fruits.append(
                    {
                        devil_fruit: {
                            "name": iron_box[devil_fruit]["name"],
                            "format_name": iron_box[devil_fruit]["format_name"],
                            "rarity": "iron_box",
                        }
                    }
                )
        for wooden_box in fruit_map["wooden_box"]:
            if devil_fruit in list(wooden_box.keys()):
                mapped_fruits.append(
                    {
                        devil_fruit: {
                            "name": wooden_box[devil_fruit]["name"],
                            "format_name": wooden_box[devil_fruit]["format_name"],
                            "rarity": "wooden_box",
                        }
                    }
                )
    return mapped_fruits


async def setup_server_id(ptero_client: PterodactylClient) -> str:
    servers = ptero_client.client.servers.list_servers()
    server_identifiers: dict = {}
    server_config: dict = {}
    for server in servers:
        for item in server.data:
            id: int = item["attributes"]["internal_id"]
            name: str = item["attributes"]["name"]
            identifier: str = item["attributes"]["identifier"]
            print(
                f"{id} : {name}",
            )
            server_identifiers[id] = identifier

    server_id: int = int(input("Please enter Server ID to monitor devil fruits for > "))

    server_config["server_id"] = server_identifiers[server_id]

    with open("server.json", "w") as f:
        json.dump(server_config, f)

    return server_config


async def get_server_config(ptero_client: PterodactylClient) -> dict:
    server_config: dict = {}
    if os.path.exists("server.json"):
        with open("server.json", "r") as f:
            server_config = json.load(f)
    else:
        return await setup_server_id(ptero_client)

    return server_config


async def get_fruits_in_inventory(nbt_data: nbt) -> list:
    fruits: list = []
    for tag in nbt_data["data"]["devilFruitsInInventories"].tags:
        if len(tag.tags) > 3:
            fruits.append(tag.tags[0])
    return [str(i) for i in fruits]


async def get_fruits_eaten(nbt_data: nbt) -> list:
    return [str(i) for i in nbt_data["data"]["ateDevilFruits"].tags]


async def get_all_fruits() -> list:
    fruits: list = []
    fruit_map: dict = {}
    with open("resources/fruits_config/fruits.json", "r") as f:
        fruit_map = json.load(f)

    for rarity in fruit_map.keys():
        for fruit_prop in fruit_map[rarity]:
            for fruit in fruit_prop.keys():
                fruits.append(fruit)
    return fruits


async def get_fruits_in_world(nbt_data: nbt) -> list:
    return [str(i) for i in nbt_data["data"]["devilFruits"]]


async def get_nbt_data(
    ptero_client: PterodactylClient, mine_mine_nbt_path: str, server_id: str
) -> nbt:

    mine_mine_nbt_file = ptero_client.client.servers.files.get_file_contents(
        server_id,
        mine_mine_nbt_path,
    ).content

    return nbt.nbt.NBTFile(fileobj=io.BytesIO(mine_mine_nbt_file))


if __name__ == "__main__":
    # TODO massive cleanups
    # TODO Readme
    with open("config.yaml") as f:
        config: dict = yaml.load(f, Loader=SafeLoader)
    try:
        discord_client.run(config["discord_api_key"])
    except KeyboardInterrupt:
        print("Bot shutting down")
