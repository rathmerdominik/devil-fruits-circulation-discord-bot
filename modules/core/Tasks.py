from io import BytesIO

from discord.ext import commands, tasks
from nbt import nbt
from utils.functions import convert_nbt_to_dict, get_ptero_file
from utils.objects import Crew


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nbt_path = "{0}/data/mineminenomi.dat".format(self.bot.config.world_name)

    async def cog_load(self):
        self.read_mmnm_nbt.start()

    async def cog_unload(self):
        self.read_mmnm_nbt.cancel()

    @tasks.loop(minutes=5)
    async def read_mmnm_nbt(self):
        """Reads the mineminenomi.dat file every 5 minutes."""
        await self.bot.modules_ready.wait()
        if not self.bot.constants.ptero_client is None:
            _file = get_ptero_file(self.bot.constants.ptero_client, self.nbt_path)
            # _file = open("mineminenomi.dat", "rb").read()
            nbt_data = nbt.NBTFile(fileobj=BytesIO(_file))
            nbt_dict = convert_nbt_to_dict(nbt_data)
            self.bot.constants.mmnm_crews = sorted(
                [Crew(**crew) for crew in nbt_dict["data"]["crews"]],
                key=lambda x: x.name,
            )
            self.bot.dispatch("mmnm_nbt_read", nbt_dict)


async def setup(bot):
    await bot.add_cog(Tasks(bot))
