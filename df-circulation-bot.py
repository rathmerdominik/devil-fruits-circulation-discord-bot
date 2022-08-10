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

@tasks.loop(minutes=1)
async def update_df_circulation():
    await discord_client.wait_until_ready()
    await discord_client.message.edit(embed=await build_formatted_message(discord_client.config, discord_client.nbt_data))
    print(f"Updated Devil Fruit Circulation {dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S')}")

    
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
    
    mine_mine_nbt_path: str = "{0}/data/mineminenomi.dat".format(config["world_name"])
    nbt_data: nbt = await stall_until_nbt_data_exists(mine_mine_nbt_path, ptero_client, server_id)
    
    channel: TextChannel = discord_client.get_channel(config["discord_channel"])
    message: Message = await get_editable_message(channel, nbt_data, config, message_id)
    
    discord_client.message = message
    discord_client.nbt_data = nbt_data
    discord_client.config = config
    
    update_df_circulation.start()
    
async def stall_until_nbt_data_exists(mine_mine_nbt_path: str, ptero_client: PterodactylClient, server_id: str)-> nbt:
    try:
        nbt_data: nbt = await get_nbt_data(ptero_client, mine_mine_nbt_path, server_id)
        return nbt_data
    
    except HTTPError as e:
        print("mineminenomi.dat not created. Wait for a player to eat a fruit first")
        sleep(60)
        stall_until_exists(mine_mine_nbt_path)


async def get_editable_message(channel: TextChannel, nbt_data: nbt,config: dict, message_id: int) -> int:
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
        await get_editable_message(channel,nbt_data,config, None)
    return message

async def build_formatted_message(config: dict, nbt_data: nbt) -> Embed:
    taken_fruits: list = await get_fruits_eaten(nbt_data) + await get_fruits_in_inventory(nbt_data)
    all_fruits: list = await get_all_fruits(nbt_data)
    fruits_available:list = list(set(all_fruits) - set(taken_fruits))
    mapped_fruits: list = await get_mapped_devil_fruits(fruits_available)

    golden_box = discord_client.get_emoji(1006270786287443978)
    iron_box = discord_client.get_emoji(1006326985934516285)
    wooden_box = discord_client.get_emoji(1006327000270655579)
    
    embed: Embed = discord.Embed(
        title="{golden}{iron}{wooden}Current Devilfruit Circulation{wooden}{iron}{golden}".format(golden=golden_box,iron=iron_box,wooden=wooden_box),
        description="__**All available Devil Fruits**__",
        color=GOLDEN_COLOR
    )
    embed.set_footer(text="Circulation is updated every minute")
    
    # TODO may god help us. This definitly has to be refactored. No idea how
    for fruit_mapped in mapped_fruits:
        for fruit_available in fruits_available:
            if fruit_available in list(fruit_mapped.keys()):
                if fruit_mapped[fruit_available]['rarity'] == "golden_box":       
                    embed.add_field(name=" \u200b",value="{rarity}{format_name}".format(rarity=golden_box, format_name=fruit_mapped[fruit_available]['format_name']), inline=True)
                elif fruit_mapped[fruit_available]['rarity'] == "iron_box":
                    embed.add_field(name=" \u200b",value="{rarity}{format_name}".format(rarity=iron_box, format_name=fruit_mapped[fruit_available]['format_name']), inline=True)
                elif fruit_mapped[fruit_available]['rarity'] == "wooden_box":
                    embed.add_field(name=" \u200b",value="{rarity}{format_name}".format(rarity=wooden_box, format_name=fruit_mapped[fruit_available]['format_name']), inline=True)
                   
    return embed



async def get_mapped_devil_fruits(devil_fruits: list) -> list:
    fruit_map: dict = {}
    mapped_fruits: list = []

    with open("resources/fruits_config/fruits.json", "r") as f:
        fruit_map = json.load(f)
    golden_box = [value for elem in fruit_map["golden_box"] for value in elem.values()]
    iron_box = [value for elem in fruit_map["iron_box"] for value in elem.values()]
    wooden_box = [value for elem in fruit_map["wooden_box"] for value in elem.values()]
    
    #TODO Wtf did i even do here. Help
    for devil_fruit in devil_fruits:
        for golden_box in fruit_map["golden_box"]:
            if devil_fruit in list(golden_box.keys()):
                mapped_fruits.append(
                    {
                        devil_fruit: {
                            "name": golden_box[devil_fruit]["name"],
                            "format_name": golden_box[devil_fruit]["format_name"],
                            "rarity": "golden_box"
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
                            "rarity": "iron_box"
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
                            "rarity": "wooden_box"
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
\
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

async def get_all_fruits(nbt_data: nbt) -> list:
    fruits: list = []
    for tag in nbt_data["data"]["devilFruits"]:
        fruits.append(tag)
    return [str(i) for i in fruits]
 

async def get_nbt_data(
    ptero_client: PterodactylClient, mine_mine_nbt_path: str, server_id: str
) -> nbt:

    mine_mine_nbt_file = ptero_client.client.servers.files.get_file_contents(
        server_id,
        mine_mine_nbt_path,
    ).content

    return nbt.nbt.NBTFile(fileobj=io.BytesIO(mine_mine_nbt_file))


if __name__ == "__main__":
    #TODO massive cleanups
    #TODO Readme
    with open("config.yaml") as f:
        config: dict = yaml.load(f, Loader=SafeLoader)
    try:
        discord_client.run(config["discord_api_key"])
    except KeyboardInterrupt:
        print("Bot shutting down")
