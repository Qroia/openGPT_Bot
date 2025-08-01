import discord
from utils.formula import ensure_decimal

def is_admin(member: discord.Member) -> bool:
    return member.guild_permissions.administrator

async def is_access(server_collection, id: str) -> bool:
    document = server_collection.find_one({"id": id})
    if document:
        if document["white_access"] == True:
            return True
    return False

async def is_balance(server_collection, id: str) -> bool:
    document = server_collection.find_one({"id": id})
    money, zero = ensure_decimal(document["money"]), ensure_decimal(0.0)
    if money > zero:
        return True
    return False