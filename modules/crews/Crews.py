import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get


class Crews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="crews", description="Lists all the crews.")
    async def crews(self, ctx, *, name: str = None):
        crew = get(self.bot.constants.mmnm_crews, name=name)
        await ctx.send(crew.name, ephemeral=True)

    @crews.autocomplete(name="name")
    async def crews_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        crews = filter(
            lambda x: current.lower() in x.name.lower(), self.bot.constants.mmnm_crews
        )
        return [app_commands.Choice(name=x.name, value=x.name) for x in crews][:25]


async def setup(bot):
    await bot.add_cog(Crews(bot))
