from decimal import Decimal

from bson.decimal128 import Decimal128
from utils.formula import ensure_decimal

async def add_white_list(server_collection, id: str):
    server_collection.insert_one({
        "id": id,
        "white_access": True,
        "money": 0.0
    })

async def set_balance(server_collection, id: str, money):
    str_id = str(id)
    document = server_collection.find_one({"id": str_id})

    current_money_decimal = ensure_decimal(document.get("money"))
    money_change_decimal = ensure_decimal(money)
    new_money_decimal = current_money_decimal + money_change_decimal
    new_money_decimal_db = Decimal128(str(new_money_decimal))

    server_collection.update_one({"id": str_id},
                                        {"$set": {"money": new_money_decimal_db}}
                                        )

async def get_server_collection(server_collection, id: str):
    str_id = str(id)
    document = server_collection.find_one({"id": str_id})
    if document:
        return document
    return None