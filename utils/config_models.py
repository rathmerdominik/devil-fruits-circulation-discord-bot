from pydactyl import PterodactylClient
from pydactyl.exceptions import ClientConfigError
from pydantic import BaseModel


class DFCircConfig(BaseModel):
    channel: int
    golden_box: int
    iron_box: int
    wooden_box: int


class BotConfig(BaseModel):
    world_name: str
    ptero_server_id: str
    ptero_server: str
    ptero_api_key: str
    discord_api_key: str
    discord_server_id: int
    bot_owners: list[int] = []
