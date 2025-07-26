import os
import discord
from discord.ext import commands
from pymongo import MongoClient
import openai
import asyncio
import config

DISCORD_BOT_TOKEN = config.DISCORD_BOT_TOKEN
OPENAI_API_KEY = config.OPENAI_API_KEY
MONGO_URI = config.MONGO_URI
GUILD_ID = config.GUILD_ID
IS_TEST = config.IS_TEST

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

try:
    openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    print("Успешно инициализирован клиент OpenAI.")
except Exception as e:
    print(f"Ошибка инициализации клиента OpenAI: {e}")
    exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client.chatgpt_discord_bot
    chats_collection = db.chats
    projects_collection = db.projects
    server_collection = db.servers
    print("Успешно подключено к MongoDB.")
except Exception as e:
    print(f"Ошибка подключения к MongoDB: {e}")
    exit(1)

@bot.event
async def on_ready():
    print(f'Бот вошел в систему как {bot.user}')
    print('------------------------------------')

    bot.chats_collection = chats_collection
    bot.projects_collection = projects_collection
    bot.server_collection = server_collection
    bot.openai_client = openai_client

    cogs_dir = "cogs"
    if not os.path.exists(cogs_dir):
        print(f"Folder '{cogs_dir}' not found. Please create it and place cogs there.")
        exit(1)

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"{cogs_dir}.{filename[:-3]}")
                print(f"Cog {filename[:-3]} loaded successfully.")
            except Exception as e:
                print(f"Ошибка при загрузке когса {filename[:-3]}: {e}")

    try:
        if IS_TEST:
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"Synchronized {len(synced)} commands to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Synchronized {len(synced)} global commands.")
    except Exception as e:
        print(f"Error synchronizing commands: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)