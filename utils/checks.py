from discord.ext import commands


def is_bot_owner():
    def predicate(ctx):
        if ctx.author.id in ctx.bot.config.bot_owners:
            return True
        return False

    return commands.check(predicate)
