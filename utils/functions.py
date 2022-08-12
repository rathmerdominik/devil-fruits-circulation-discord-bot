from io import BytesIO
from pathlib import Path

import yaml
from discord.utils import get
from nbt import nbt
from nbt.nbt import TAG_Compound, TAG_Int, TAG_List, TAG_Long, TAG_String
from pydactyl import PterodactylClient

from utils.objects import DevilFruit


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def convert_nbt_to_dict(data: nbt.NBTFile) -> dict:
    as_dict = {}
    for key, value in data.iteritems():
        if isinstance(value, TAG_Compound):
            as_dict[key] = convert_nbt_to_dict(value)
        elif isinstance(value, TAG_List):
            as_dict[key] = [convert_nbt_to_dict(list_value) for list_value in value]
        elif isinstance(value, (TAG_String, TAG_Int, TAG_Long)):
            as_dict[key] = value.value
        else:
            as_dict[key] = value
    return as_dict


def get_ptero_file(
    ptero_client: PterodactylClient, path: str, server_id: str
) -> nbt.NBTFile:
    mine_mine_nbt_file = ptero_client.client.servers.files.get_file_contents(
        server_id,
        path,
    ).content
    return nbt.NBTFile(fileobj=BytesIO(mine_mine_nbt_file))


async def load_nbt(config, path) -> nbt.NBTFile:
    try:
        return get_ptero_file(config.ptero_client, path, config.server_id)
    except Exception as e:
        print("mineminenomi.dat not existing. Wait for a player to choose a race")


def yaml_load(path: Path, config_name="config.yaml") -> dict:
    config = path.joinpath(config_name)
    if not config.exists():
        raise Exception(config_name)
    return yaml.safe_load(open(config, "r"))


def list_devil_fruits(data: dict):
    for rarity, fruits in data.items():
        for fruit in fruits:
            for qualified_name, devil_fruit in fruit.items():
                yield DevilFruit(
                    rarity=rarity, qualified_name=qualified_name, **devil_fruit
                )


def list_golden_devil_fruits(data: list[DevilFruit]):
    return list(filter(lambda x: x.rarity == "golden_box", data))


def list_iron_devil_fruits(data: list[DevilFruit]):
    return list(filter(lambda x: x.rarity == "iron_box", data))


def list_wooden_devil_fruits(data: list[DevilFruit]):
    return list(filter(lambda x: x.rarity == "wooden_box", data))


def list_eaten_fruits(data: list[DevilFruit], nbt_data: dict):
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
    inventory_fruits = nbt_data["data"].get("devilFruitsInInventories", [])
    fruits = []
    for inventory in inventory_fruits:
        for i in range(inventory.get("fruits")):
            if fruit_name := inventory.get(f"fruit-{i}"):
                fruits.append(get(data, qualified_name=fruit_name))
    return fruits
