import discord
import config
from discord.ext import commands
from utils.admin import add_white_list, get_server_collection, set_balance

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_collection = bot.server_collection
        self.owner = config.OWNER_ID

    @discord.app_commands.command(name="setbalance", description="Добавление баланса")
    @discord.app_commands.describe(id="Айди сервера",balance="Значение +баланса")
    async def setbalance(self, interaction: discord.Interaction, id: str, balance: str):
        if interaction.user.id != self.owner:
            await interaction.response.send_message("Вы не являетесь администратором", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True) 
        try:
            await set_balance(self.server_collection, str(id), float(balance))
            updated_document = await get_server_collection(self.server_collection, str(id))
            await interaction.followup.send(f"Баланс добавлен. Текущий баланс: {updated_document["money"]}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Ошибка при добавление баланса: {e}", ephemeral=True)
    
    @discord.app_commands.command(name="addserver", description="Добавление сервера в белый список")
    @discord.app_commands.describe(id="ID Сервера")
    async def addserver(self, interaction: discord.Interaction, id: str):
        if interaction.user.id != self.owner:
            await interaction.response.send_message("Вы не являетесь администратором", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True) 
        try:
            await add_white_list(self.server_collection, id)
            await interaction.followup.send("Сервер добавлен.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Ошибка при добавление баланса: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))