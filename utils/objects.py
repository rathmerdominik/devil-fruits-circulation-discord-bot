import os
from pydantic import BaseModel
from pathlib import Path


class Object:
    ...


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


class DevilFruit(BaseModel):
    name: str
    format_name: str
    qualified_name: str
    rarity: str


class Module(BaseModel):
    base_path: Path
    path: Path

    @property
    def name(self):
        return self.path.stem

    @property
    def qualified_name(self):
        return self.path.name

    @property
    def relative_path(self):
        return self.path.relative_to(Path.cwd())

    @property
    def spec(self):
        return ".".join(
            str(self.path.relative_to(self.base_path)).split(os.sep)
        ).replace(".py", "")
