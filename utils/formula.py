import config
from decimal import Decimal

def price_formula(tokens: int, model: str) -> Decimal:
    return Decimal(str((tokens / 10000 ) * config.GPT_PRICE_MODELS[model]))

def ensure_decimal(value):
    if isinstance(value, (float, int)):
        return Decimal(str(value)) 
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))