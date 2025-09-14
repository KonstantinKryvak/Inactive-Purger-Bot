

from .connection                    import Client
from datetime                       import datetime, timedelta
from logging                        import getLogger
from telethon.tl.types              import ChannelParticipantsRecent, ChatBannedRights, UserStatusOffline
from telethon.tl.functions.channels import EditBannedRequest, GetParticipantsRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler


__log__ = getLogger(__name__)

async def ReceiveInactiveList(chat, threshold):
    cutoff = datetime.now() - timedelta(days=threshold)
    result = await Client.Account(GetParticipantsRequest(chat, ChannelParticipantsRecent(), 0, 100, hash=0))
    inactive = []
    for user in result.users:
        if isinstance(user.status, UserStatusOffline):
            if user.status.was_online < cutoff:
                inactive.append(user)
    __log__.info(f"{chat.title}: Found {len(inactive)} inactive users.")
    return inactive


async def PruneUsers(chat, users):
    rights = ChatBannedRights(until_date=None, view_messages=True)
    for user in users:
        try:
            await Client.Account(EditBannedRequest(chat, user.id, rights))
            __log__.info(f"Pruned user {user.id} from {chat.title}")
        except Exception as e:
            __log__.error(f"Failed to prune user {user.id} from {chat.title}: {e}")


async def DoPrune(chatID, threshold):
    __log__.info(f'Scheduled cleanup begins for chat: {chatID}...')
    try:
        entity = await Client.Account.get_entity(chatID)
        inactive = await ReceiveInactiveList(entity, threshold)
        await PruneUsers(entity, inactive)
        __log__.info(f"Scheduled cleanup complete for chat {chatID}.")
    except Exception as e:
        __log__.error(f"Error during cleanup for chat {chatID}: {e}.")


