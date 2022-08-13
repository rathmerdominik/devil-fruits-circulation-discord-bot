from io import BytesIO
from pathlib import Path
from typing import Iterable

import yaml
from aiohttp import ClientSession
from discord.utils import get
from nbt import nbt
from nbt.nbt import TAG_Compound, TAG_Int, TAG_List, TAG_Long, TAG_String, TAG_Byte
from pydactyl import PterodactylClient

from utils.objects import DevilFruit, MinecraftPlayer, Module


def chunks(l: Iterable, n: int) -> Iterable:
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def convert_nbt_to_dict(data: nbt.NBTFile) -> dict:
    """Convert nbt file to dict."""
    as_dict = {}
    for key, value in data.iteritems():
        if isinstance(value, TAG_Compound):
            as_dict[key] = convert_nbt_to_dict(value)
        elif isinstance(value, TAG_List):
            as_dict[key] = [convert_nbt_to_dict(list_value) for list_value in value]
        elif isinstance(value, (TAG_String, TAG_Int, TAG_Long, TAG_Byte)):
            as_dict[key] = value.value
        else:
            as_dict[key] = value
    return as_dict


def get_ptero_file(ptero_client: PterodactylClient, path: str, server_id: str) -> bytes:
    """Get a nbt file from pterodactyl server."""
    return ptero_client.client.servers.files.get_file_contents(
        server_id,
        path,
    ).content


def yaml_load(path: Path, config_name: str = "config.yaml") -> dict:
    """Load a yaml file as a dict."""
    config = path.joinpath(config_name)
    if not config.exists():
        raise Exception(config_name)
    return yaml.safe_load(open(config, "r"))


def list_devil_fruits(data: dict):
    """List all devil fruits."""
    for rarity, fruits in data.items():
        for fruit in fruits:
            for qualified_name, devil_fruit in fruit.items():
                yield DevilFruit(
                    rarity=rarity, qualified_name=qualified_name, **devil_fruit
                )


def list_golden_devil_fruits(data: list[DevilFruit]):
    """List all golden box devil fruits."""
    return list(filter(lambda x: x.rarity == "golden_box", data))


def list_iron_devil_fruits(data: list[DevilFruit]):
    """List all iron box devil fruits."""
    return list(filter(lambda x: x.rarity == "iron_box", data))


def list_wooden_devil_fruits(data: list[DevilFruit]):
    """List all wooden box devil fruits."""
    return list(filter(lambda x: x.rarity == "wooden_box", data))


def list_eaten_fruits(data: list[DevilFruit], nbt_data: dict):
    """List all devil fruits eaten by players."""
    eaten_fruits = nbt_data["data"].get("ateDevilFruits")
    if eaten_fruits is None:
        return []
    return list(
        filter(
            lambda x: x.qualified_name in eaten_fruits.values(),
            data,
        )
    )


def list_inventory_fruits(data: list[DevilFruit], nbt_data: dict):
    """List all devil fruits in inventories."""
    inventory_fruits = nbt_data["data"].get("devilFruitsInInventories", [])
    fruits = []
    for inventory in inventory_fruits:
        for i in range(inventory.get("fruits")):
            if fruit_name := inventory.get(f"fruit-{i}"):
                fruits.append(get(data, qualified_name=fruit_name))
    return fruits


def get_modules(path: Path) -> Iterable[Module]:
    """Get all modules in the modules folder recursively."""
    for module in path.rglob("*.py"):
        yield Module(base_path=path.parent, path=module)


async def get_mc_player(session: ClientSession, player_id: str) -> dict:
    """Get a player from the api."""
    async with session.get(
        f"https://sessionserver.mojang.com/session/minecraft/profile/{player_id}"
    ) as r:
        return MinecraftPlayer(await r.json())
