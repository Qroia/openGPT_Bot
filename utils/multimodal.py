import config

def is_multimodal(model: str) -> bool:
    if model in config.MULTIMODAL_MODELS:
        return True
    return False