import base64
import requests

async def get_image_as_base64_data_url(image_url: str) -> str:
    """
    Загружает изображение по URL и преобразует его в Base64 Data URL.
    """
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status() # Вызовет исключение для ошибок HTTP

        content_type = response.headers.get('Content-Type')
        if not content_type or not content_type.startswith('image/'):
            raise ValueError(f"URL не указывает на изображение: {content_type}")

        image_bytes = response.content
        base64_encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Создаем Data URL
        data_url = f"data:{content_type};base64,{base64_encoded_image}"
        return data_url
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке изображения: {e}")
        raise
    except ValueError as e:
        print(f"Ошибка: {e}")
        raise