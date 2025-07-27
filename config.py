import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
LOCAL_TYPE = os.getenv("LOCAL_TYPE")
LOCAL_MODELS_URI = os.getenv("LOCAL_MODELS_URI")

SUPPORTED_MODELS = ["chatgpt-4o-latest", "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "o3-mini", "o4-mini", "o1", "o3-pro", "o3"]
MODELS_WITHOUT_TEMPERATURE = ["o1", "o3-pro", "o3", "o3-mini", "o4-mini"]
DEEPSEEK_MODELS = ["r1", "v3"]
GEMINI_MODELS = ["2.5-flash", "2.5-pro"]
MULTIMODAL_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o3", "o3-pro", "o4-mini", "o1"]
#LOCAL_MODELS = get_local_models(LOCAL_TYPE, LOCAL_MODELS_URI)

INDIVIDUAL_MAX_TOKENS_PER_CHAT = 15000
PROJECT_MAX_TOKENS_PER_CHAT = 45000


# PER 10.000
C_PRICE = 1.5
GPT_PRICE_MODELS = {
    "chatgpt-4o-latest": 0.12 * C_PRICE,
    "gpt-4o": 0.05 * C_PRICE,
    "gpt-4o-mini": 0.003 * C_PRICE,
    "o3-pro": 0.5 * C_PRICE,
    "o3": 0.03 * C_PRICE,
    "o3-mini": 0.015 * C_PRICE,
    "gpt-4.1": 0.03 * C_PRICE,
    "gpt-4.1-mini": 0.006 * C_PRICE,
    "gpt-4.1-nano": 0.0025 * C_PRICE,
    "o4-mini": 0.017 * C_PRICE,
}

# ONLY FOR TEST
GUILD_ID = os.getenv("GUILD_ID")
OWNER_ID = 1275890102052061360
IS_TEST = False

if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN is not set in environment variables.")
    exit(1)
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY is not set in environment variables.")
    exit(1)
if not MONGO_URI:
    print("Error: MONGO_URI is not set in environment variables.")
    exit(1)
