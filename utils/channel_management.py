import tiktoken
import config
from utils.tobase64 import get_image_as_base64_data_url

async def get_channel_settings(chats_collection, channel_id: int) -> dict | None:
    settings = chats_collection.find_one({"channel_id": str(channel_id)})
    if settings:
        if 'history' not in settings or not isinstance(settings['history'], list):
            settings['history'] = []
        return settings
    return None

async def update_channel_settings(chats_collection, channel_id: int, updates: dict):
    chats_collection.update_one(
        {"channel_id": str(channel_id)},
        {"$set": updates},
        upsert=True
    )

async def add_message_to_channel_history(chats_collection: str, channel_id: int, role: str, content: str, image) -> list:
    settings = await get_channel_settings(chats_collection, channel_id)

    if not settings:
        settings = {
            "channel_id": str(channel_id),
            "model": "gpt-4.1-mini",
            "temperature": 0.7,
            "global_message": None,
            "history": [],
            "is_project_chat": False
        }
        await update_channel_settings(chats_collection, channel_id, settings)

    settings["model"] = "gpt-4o"

    history = settings.get("history", [])
    if image:
        base64_image_data_url = await get_image_as_base64_data_url(image[0])
        history.append({"role": role, "content": [
            {"type": "text", "text": content},
            {
                "type": "image_url",
                "image_url": {
                    "url": base64_image_data_url,
                    "detail": "high"
                },
            },
        ]})
    else:
        history.append({"role": role, "content": content})

    encoding = tiktoken.encoding_for_model(settings.get("model", "gpt-4o"))
    current_tokens = 0
    for m in history:
        if isinstance(m["content"], str):
            current_tokens += len(encoding.encode(m["content"]))
        else:
            current_tokens += len(encoding.encode(m["content"][0]["text"])) + 2000

    while current_tokens > config.INDIVIDUAL_MAX_TOKENS_PER_CHAT and len(history) > 1:
        if settings.get("global_message") and history[0].get("role") == "system":
            removed_message = history.pop(1)
        else:
            removed_message = history.pop(0)
        if isinstance(m["content"], str):
            current_tokens -= len(encoding.encode(removed_message["content"]))
        else:
            current_tokens -= len(encoding.encode(removed_message["content"][0]["text"])) - 2000

    await update_channel_settings(chats_collection, channel_id, {"history": history})
    return history, current_tokens