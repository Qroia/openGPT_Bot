import discord
from discord.ext import commands
import openai

from utils.admin import get_server_collection, set_balance
from utils.formula import price_formula
from utils.lmstudio_interface import lm_respond_message
from utils.permissions import is_access, is_admin
from utils.multimodal import is_multimodal
from utils.channel_management import get_channel_settings, update_channel_settings, add_message_to_channel_history
from utils.project_management import get_project_settings, update_project_settings, add_message_to_project_history
import config

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chats_collection = bot.chats_collection
        self.projects_collection = bot.projects_collection
        self.server_collection = bot.server_collection
        self.openai_client = bot.openai_client

    async def _get_chat_context(self, channel_id: int, category_id: int = None):
        project_settings = None
        if category_id:
            project_settings = await get_project_settings(self.projects_collection, category_id)

        if project_settings:
            return (
                True,
                project_settings,
                project_settings.get("history", []),
                self.projects_collection,
                project_settings.get("token_limit", config.PROJECT_MAX_TOKENS_PER_CHAT)
            )
        else:
            channel_settings = await get_channel_settings(self.chats_collection, channel_id)
            return (
                False,
                channel_settings,
                channel_settings.get("history", []) if channel_settings else [],
                self.chats_collection,
                config.INDIVIDUAL_MAX_TOKENS_PER_CHAT
            )

    # --- Bot Events ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if message.guild is None:
            return
        
        if not await is_access(self.server_collection, str((message.guild.id))):
            return

        if not is_admin(message.author):
            if not message.content.startswith(self.bot.command_prefix):
                return
            pass

        category_id = message.channel.category.id if message.channel.category else None
        is_project_chat, current_settings, current_history, collection_to_use, token_limit_to_use = \
            await self._get_chat_context(message.channel.id, category_id)

        if is_project_chat and current_settings.get("general_channel_id") == str(message.channel.id) and \
           not message.content.startswith(self.bot.command_prefix):
            await message.channel.send("Этот канал предназначен только для управления настройками проекта. Для чата с ИИ используйте другие каналы в этой категории.")
            return

        if not message.content.startswith(self.bot.command_prefix) and current_settings:
            try:
                async with message.channel.typing():
                    attachments_message = []
                    if message.attachments:
                        for attachment in message.attachments:
                            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                attachments_message.append(attachment.url)

                    if len(attachments_message) > 0 and is_multimodal(current_settings["model"]):
                        if is_project_chat:
                            history_updated, _ = await add_message_to_project_history(
                                self.projects_collection, category_id, "user", message.content, attachments_message
                            )
                        else:
                            history_updated, _ = await add_message_to_channel_history(
                                self.chats_collection, message.channel.id, "user", message.content, attachments_message
                            )
                    else:
                        if is_project_chat:
                            history_updated, _ = await add_message_to_project_history(
                                self.projects_collection, category_id, "user", message.content, False
                            )
                        else:
                            history_updated, _ = await add_message_to_channel_history(
                                self.chats_collection, message.channel.id, "user", message.content, False
                            )

                    messages_for_openai = []
                    if current_settings.get("global_message"):
                        messages_for_openai.append({"role": "system", "content": current_settings["global_message"]})
                    messages_for_openai.extend(history_updated)

                    if current_settings["model"] in config.MODELS_WITHOUT_TEMPERATURE:
                        response = await self.openai_client.chat.completions.create(
                            model=current_settings.get("model", "gpt-4.1-mini"),
                            messages=messages_for_openai,
                        )
                    else:
                        response = await self.openai_client.chat.completions.create(
                            model=current_settings.get("model", "gpt-4.1-mini"),
                            messages=messages_for_openai,
                            temperature=current_settings.get("temperature", 0.7),
                        )
                    
                    chat_response = response.choices[0].message.content

                    if is_project_chat:
                        _, current_tokens = await add_message_to_project_history(
                            self.projects_collection, category_id, "assistant", chat_response, False
                        )
                    else:
                        _, current_tokens = await add_message_to_channel_history(
                            self.chats_collection, message.channel.id, "assistant", chat_response, False
                        )

                    await set_balance(self.server_collection, message.guild.id, -price_formula(current_tokens, current_settings.get("model")))
                    
                    # SMART RENAME CHANNEL
                    channel_name = message.channel.name
                    channel_id = message.channel.id
                    if "chat-gpt-" in channel_name:
                        lm_response = await lm_respond_message([message.content, chat_response])
                        channel = self.bot.get_channel(channel_id)
                        await channel.edit(name=str(lm_response))

                    # SEND BLOCK
                    chunks = [chat_response[i:i+2000] for i in range(0, len(chat_response), 2000)]
                    
                    for chunk in chunks:
                        await message.channel.send(chunk)

            except openai.APIStatusError as e:
                await message.channel.send(f"Произошла ошибка при обращении к OpenAI: `{e}`")
                print(f"OpenAI API Error: {e}")
            except Exception as e:
                await message.channel.send(f"Произошла непредвиденная ошибка: `{e}`")
                print(f"Unexpected Error: {e}")
        
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.TextChannel):
            if self.chats_collection.find_one({"channel_id": str(channel.id), "is_project_chat": False}):
                self.chats_collection.delete_one({"channel_id": str(channel.id)})
                print(f"Данные для индивидуального канала {channel.name} ({channel.id}) удалены из базы данных.")
            
            if channel.category:
                project_settings = await get_project_settings(self.projects_collection, channel.category.id)
                if project_settings and project_settings.get("general_channel_id") == str(channel.id):

                    self.projects_collection.delete_one({"category_id": str(channel.category.id)})
                    self.chats_collection.delete_many({"project_id": str(channel.category.id)})
                    print(f"Проект {channel.category.name} ({channel.category.id}) и все его чаты удалены из базы данных, т.к. был удален основной канал.")


    @commands.Cog.listener()
    async def on_guild_category_delete(self, category: discord.CategoryChannel):
        if self.projects_collection.find_one({"category_id": str(category.id)}):
            self.projects_collection.delete_one({"category_id": str(category.id)})

            deleted_chats_count = self.chats_collection.delete_many({"project_id": str(category.id)}).deleted_count
            print(f"Проект {category.name} ({category.id}) и {deleted_chats_count} связанных чатов удалены из базы данных.")

    # --- Bot Commands ---

    # Decorator to check administrator permissions
    async def check_admin_interaction(self, interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            await interaction.response.send_message("You do not have administrator rights to use this command.", ephemeral=True)
            return False
        return True

    @discord.app_commands.command(name="newchat", description="Создает новый чат-канал с ChatGPT (индивидуальный или в проекте).")
    async def newchat(self, interaction: discord.Interaction):
        if not await self.check_admin_interaction(interaction):
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Эту команду можно использовать только на сервере.", ephemeral=True)
            return

        category = interaction.channel.category if interaction.channel and isinstance(interaction.channel, discord.TextChannel) else None
        project_settings = None
        if category:
            project_settings = await get_project_settings(self.projects_collection, category.id)

        target_category = category
        is_project_context = False

        if project_settings:
            is_project_context = True
            await interaction.response.defer(ephemeral=False)
        else:
            for cat in guild.categories:
                if cat.name == "All chats":
                    target_category = cat
                    break
            if not target_category or target_category.name != "All chats":
                try:
                    target_category = await guild.create_category("All chats")
                    await interaction.followup.send(f"Создана новая категория: **All chats**.", ephemeral=False)
                except discord.Forbidden:
                    await interaction.response.send_message("У меня нет прав для создания категорий.", ephemeral=True)
                    return
                except Exception as e:
                    await interaction.response.send_message(f"Ошибка при создании категории: {e}", ephemeral=True)
                    return
            await interaction.response.defer(ephemeral=False)

        try:
            channel_name = f"chat-gpt-{len(target_category.channels) + 1}"
            new_channel = await guild.create_text_channel(channel_name, category=target_category)

            if is_project_context:
                await update_channel_settings(
                    self.chats_collection,
                    new_channel.id,
                    {
                        "guild_id": str(guild.id),
                        "category_id": str(target_category.id),
                        "project_id": str(target_category.id),
                        "is_project_chat": True
                    }
                )
                await interaction.followup.send(f"Новый чат проекта создан: {new_channel.mention}", ephemeral=False)
            else:
                await update_channel_settings(
                    self.chats_collection,
                    new_channel.id,
                    {
                        "guild_id": str(guild.id),
                        "category_id": str(target_category.id),
                        "model": "gpt-4.1-mini",
                        "temperature": 0.7,
                        "global_message": None,
                        "history": [],
                        "is_project_chat": False
                    }
                )
                await interaction.followup.send(f"Новый индивидуальный чат создан: {new_channel.mention}", ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("У меня нет прав для создания каналов в этой категории.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ошибка при создании чата: {e}", ephemeral=True)


    @discord.app_commands.command(name="newproject", description="Создает новую категорию (проект) и чат 'General' в ней.")
    @discord.app_commands.describe(name="Название новой категории (проекта).")
    async def newproject(self, interaction: discord.Interaction, name: str):
        if not await self.check_admin_interaction(interaction):
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Эту команду можно использовать только на сервере.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        try:
            new_category = await guild.create_category(name)
            await interaction.followup.send(f"Создана новая категория (проект): **{new_category.name}**", ephemeral=False)

            general_channel = await guild.create_text_channel("general", category=new_category)

            await update_project_settings(
                self.projects_collection,
                new_category.id,
                {
                    "guild_id": str(guild.id),
                    "category_id": str(new_category.id),
                    "project_name": name,
                    "general_channel_id": str(general_channel.id),
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "global_message": None,
                    "history": [],
                    "token_limit": config.PROJECT_MAX_TOKENS_PER_CHAT
                }
            )

            await update_channel_settings(
                self.chats_collection,
                general_channel.id,
                {
                    "guild_id": str(guild.id),
                    "category_id": str(new_category.id),
                    "project_id": str(new_category.id),
                    "is_project_chat": True
                }
            )
            await interaction.followup.send(f"Чат 'general' создан в категории {new_category.mention}: {general_channel.mention}. Этот канал предназначен для настроек проекта.", ephemeral=False)

        except discord.Forbidden:
            await interaction.followup.send("У меня нет прав для создания категорий или каналов.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ошибка при создании проекта: {e}", ephemeral=True)


    @discord.app_commands.command(name="setmodel", description="Устанавливает модель ChatGPT для текущего чата/проекта.")
    @discord.app_commands.describe(model="Название модели (например, gpt-4.1-mini, gpt-4o).")
    async def setmodel(self, interaction: discord.Interaction, model: str):
        if not await self.check_admin_interaction(interaction):
            return

        category_id = interaction.channel.category.id if interaction.channel.category else None
        is_project_chat, current_settings, _, collection_to_use, _ = \
            await self._get_chat_context(interaction.channel_id, category_id)

        if not current_settings:
            await interaction.response.send_message("Этот канал не является чатом, управляемым ботом, или не принадлежит проекту.", ephemeral=True)
            return

        if model.lower() not in config.SUPPORTED_MODELS:
            await interaction.response.send_message(
                f"Неподдерживаемая модель. Поддерживаемые модели: {', '.join(config.SUPPORTED_MODELS)}",
                ephemeral=True
            )
            return

        if is_project_chat:
            await update_project_settings(self.projects_collection, category_id, {"model": model.lower()})
            await interaction.response.send_message(f"Модель для этого **проекта** установлена на: `{model}`", ephemeral=False)
        else:
            await update_channel_settings(self.chats_collection, interaction.channel_id, {"model": model.lower()})
            await interaction.response.send_message(f"Модель для этого **чата** установлена на: `{model}`", ephemeral=False)


    @discord.app_commands.command(name="setglobalmessage", description="Устанавливает системное сообщение для текущего чата/проекта.")
    @discord.app_commands.describe(message="Системное сообщение (оставьте пустым для удаления).")
    async def setglobalmessage(self, interaction: discord.Interaction, message: str = None):
        if not await self.check_admin_interaction(interaction):
            return

        category_id = interaction.channel.category.id if interaction.channel.category else None
        is_project_chat, current_settings, _, collection_to_use, _ = \
            await self._get_chat_context(interaction.channel_id, category_id)

        if not current_settings:
            await interaction.response.send_message("Этот канал не является чатом, управляемым ботом, или не принадлежит проекту.", ephemeral=True)
            return

        if is_project_chat:
            if not message:
                await update_project_settings(self.projects_collection, category_id, {"global_message": None})
                await interaction.response.send_message("Системное сообщение для этого **проекта** удалено.", ephemeral=False)
            else:
                await update_project_settings(self.projects_collection, category_id, {"global_message": message})
                await interaction.response.send_message(f"Системное сообщение для этого **проекта** установлено: `{message}`", ephemeral=False)
        else:
            if not message:
                await update_channel_settings(self.chats_collection, interaction.channel_id, {"global_message": None})
                await interaction.response.send_message("Системное сообщение для этого **чата** удалено.", ephemeral=False)
            else:
                await update_channel_settings(self.chats_collection, interaction.channel_id, {"global_message": message})
                await interaction.response.send_message(f"Системное сообщение для этого **чата** установлено: `{message}`", ephemeral=False)


    @discord.app_commands.command(name="settemperature", description="Устанавливает температуру для текущего чата/проекта (0.0 - 2.0).")
    @discord.app_commands.describe(temperature="Значение температуры (например, 0.7).")
    async def settemperature(self, interaction: discord.Interaction, temperature: float):
        if not await self.check_admin_interaction(interaction):
            return

        category_id = interaction.channel.category.id if interaction.channel.category else None
        is_project_chat, current_settings, _, collection_to_use, _ = \
            await self._get_chat_context(interaction.channel_id, category_id)

        if not current_settings:
            await interaction.response.send_message("Этот канал не является чатом, управляемым ботом, или не принадлежит проекту.", ephemeral=True)
            return

        if not (0.0 <= temperature <= 2.0):
            await interaction.response.send_message("Температура должна быть числом от 0.0 до 2.0.", ephemeral=True)
            return

        if is_project_chat:
            await update_project_settings(self.projects_collection, category_id, {"temperature": temperature})
            await interaction.response.send_message(f"Температура для этого **проекта** установлена на: `{temperature}`", ephemeral=False)
        else:
            await update_channel_settings(self.chats_collection, interaction.channel_id, {"temperature": temperature})
            await interaction.response.send_message(f"Температура для этого **чата** установлена на: `{temperature}`", ephemeral=False)

    @discord.app_commands.command(name="myaccount", description="Просмотр баланса")
    async def myaccount(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) 
        try:
            account = await get_server_collection(self.server_collection, str(interaction.guild.id))
            if account:
                await interaction.followup.send(f"Баланс: `{account['money']}`\nДоступ: {account['white_access']}", ephemeral=True)
            else:
                await interaction.followup.send("Ваш сервер не найден в базе данных.", ephemeral=True)        
        except Exception as e:
            await interaction.followup.send(f"Ошибка при создании проекта: {e}", ephemeral=True)

    @discord.app_commands.command(name="price_list", description="Просмотр стоимости моделей")
    async def price_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) 
        try:
            text = "Стоимость высех моделей(За 10.000Токенов):\n"
            for key, val in config.GPT_PRICE_MODELS.items():
                text += f"{key} - {val:.5f}$\n"
            await interaction.followup.send(text, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Ошибка при создании проекта: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))