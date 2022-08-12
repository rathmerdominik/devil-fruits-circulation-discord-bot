from pydantic import BaseModel


class Object:
    ...


class DFCircConfig(BaseModel):
    channel: int
    golden_box: int
    iron_box: int
    wooden_box: int


class BotConfig(BaseModel):
    world_name: str
    discord_api_key: str
    ptero_server_id: str
    ptero_server: str
    ptero_api_key: str


class DevilFruit(BaseModel):
    name: str
    format_name: str
    qualified_name: str
    rarity: str
