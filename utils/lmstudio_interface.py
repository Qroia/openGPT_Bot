import config
import asyncio
import lmstudio as lms

async def lm_respond_message(message_list: list) -> str:
    SERVER_URL = config.LOCAL_MODELS_URI
    lms.configure_default_client(SERVER_URL)
    llm = lms.llm("gemma-3-1b-it")

    response = await asyncio.to_thread(llm.respond, f"""
    ТВОЯ ЗАДАЧА: ОТВЕТИТЬ МАКИСИМАЛЬНО КРАТКО И ПО СТУИ НИЧЕГО ЛИШНЕГО.
    НА ОСНОВЕ НИЖЕ ПРИВЕДЁННОЙ ПЕРЕПИСКЕ СОЗДАЙ НАЗВАНИЕ ЧАТА КОРОТКОЕ ДЛЯ DISCORD КАНАЛА. ОГРАНИЧЕНИЕ 4 СЛОВА. ОГРАНИЧЕНИЕ: НЕЛЬЗЯ ИСПОЛЬЗОВАТЬ СПЕЦИАЛЬНЫЕ СИМВОЛЫ, ЗАПЯТЫЕ, ТОЧКИ и ДР. ТОЛЬКО БУКВЫ И ЦИФРЫ
    
    Пользователь: {message_list[0]}

    АССИСТЕНТ: {message_list[1]}
    """)

    return str(response)