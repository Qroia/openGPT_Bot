import discord

def is_admin(member: discord.Member) -> bool:
    return member.guild_permissions.administrator

async def is_access(server_collection, id: str) -> bool:
    document = server_collection.find_one({"id": id})
    if document:
        if document["white_access"] == True:
            return True
    return False