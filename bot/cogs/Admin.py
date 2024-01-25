from discord.ext import commands

from config import bot_config


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        await bot_config.NOTIFY_TO_OWNER(self.bot, "Ready!")


def setup(bot):
    return bot.add_cog(Admin(bot))
