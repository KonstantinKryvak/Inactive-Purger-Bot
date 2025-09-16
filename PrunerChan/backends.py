

import logging, asyncio, json, sys, os, re, io

# Custom formatter with level-based styles
class LevelFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:    f'\033[38;5;242m%(asctime)s %(module)s - %(message)s\033[0m',
        logging.INFO:     f'\033[38;5;242m%(asctime)s %(module)s - \033[38;5;51m%(message)s\033[0m',
        logging.WARNING:  f'\033[38;5;242m%(asctime)s %(module)s - \033[38;5;208m%(message)s\033[0m',
        logging.ERROR:    f'\033[38;5;242m%(asctime)s %(module)s - \033[38;5;196m%(message)s\033[0m',
        logging.CRITICAL: f'\033[38;5;242m%(asctime)s %(module)s - \033[38;5;93m%(message)s\033[0m'
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self._fmt)
        self._style._fmt = fmt
        record.module = f'{record.module:^16}'
        return super().format(record)

# Global logging setup (INFO+ only)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

streamhandler = logging.StreamHandler(sys.stdout)
filehandler = logging.FileHandler('session.log')

filehandler.setFormatter(LevelFormatter(datefmt='%d-%m-%Y %H:%M:%S'))
root_logger.addHandler(filehandler)
root_logger.addHandler(streamhandler)

# Custom logger with DEBUG level
logger = logging.getLogger("Logger")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Prevent duplication via root logger

streamhandler.setFormatter(LevelFormatter(datefmt='%d-%m-%Y %H:%M:%S'))
logger.addHandler(streamhandler)
logger.addHandler(filehandler)



from os                             import environ as env
from datetime                       import datetime, timedelta
from telethon                       import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types              import (ChannelParticipantAdmin, ChannelParticipantCreator,
                                            UserStatusOnline, UserStatusOffline, UserStatusRecently,
                                            UserStatusLastWeek, UserStatusLastMonth, UserStatusEmpty)
from telethon.errors                import UserNotParticipantError



client = TelegramClient('anon', env['api-ID'], env['api-hash']).start(bot_token=env['bot-token'])


class Config:
    dry: bool       = False
    datadir: str    = '__data__/'

    selections: str = 'selections.json'
    dialogs: str    = 'active-dialogs.json'


async def prune_inactive_users(client, chat_id, threshold, dry_run=False, whitelist=None, delay=1.0):
    logger.debug(f'Initializing prune operation for channel ID: \"{chat_id}\"')
    if whitelist is None:
        logger.warning(u'No users reserved in a whitelist...')
        whitelist = []

    removed = []
    skipped = []

    async for user in client.iter_participants(chat_id):
        user_id = user.id
        username = user.username or f"{user.first_name} {user.last_name or ''}".strip()

        # Skip whitelisted users
        if user_id in whitelist:
            skipped.append((user_id, username, "Whitelisted"))
            logger.debug(f'Skipped whitelisted user: \"{username}\" (id: {user_id}).')
            continue

        # Skip admins and creators
        try:
            participant = await client(GetParticipantRequest(chat_id, user_id))
            if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                skipped.append((user_id, username, "Admin"))
                logger.debug(f'Skipped Administrator: \"{username}\" (id: {user_id})')
                continue
        except Exception as e:
            skipped.append((user_id, username, f"Error checking admin: {e}"))
            continue

        # Check last seen
        
        last_seen:datetime = datetime.now()
        if isinstance(user.status, UserStatusOnline):
            last_seen = user.status.expires
            logger.debug(f'{username}\'s status is \"Online\". Status expires: \"{user.status.expires.strftime('%d-%m-%Y %H:%M:%S')}\"')
        elif isinstance(user.status, UserStatusOffline):
            last_seen = user.status.was_online
            logger.debug(f'{username}\'s status is \"Offline\". Last seen: \"{user.status.was_online.strftime('%d-%m-%Y %H:%M:%S')}\"')
        elif isinstance(user.status, UserStatusRecently):
            last_seen = datetime.now() - timedelta(days=1)
            logger.debug(f'{username}\'s status is \"Was seen recently...\"')
        elif isinstance(user.status, UserStatusLastWeek):
            last_seen = datetime.now() - timedelta(days=7)
            logger.debug(f'{username}\'s status is \"Was seen last week...\"')
        elif isinstance(user.status, UserStatusLastMonth):
            last_seen = datetime.now() - timedelta(days=30)
            logger.debug(f'{username}\'s status is \"Was seen last month...\"')
        elif isinstance(user.status, UserStatusEmpty) or not user.status:
            last_seen = datetime.now() - timedelta(days=365)
            logger.debug(f'{username}\'s status is \"Was seen long time ago...\" or has no status at all.')

        if (datetime.now() - last_seen) > threshold:
            if dry_run:
                removed.append((user_id, username, last_seen, "Would be removed"))
                logger.debug(f'[Dry run] User would\'ve been removed: \"{username}\" (id: {user_id}, last seen: {last_seen.strftime("%d-%m-%Y %H:%M:%S")}).')
            else:
                try:
                    await client.kick_participant(chat_id, user_id)
                    removed.append((user_id, username, last_seen, "Was inactive"))
                    logger.debug(f'Successfully removed a user: \"{username}\" (id: {user_id}).')
                    await asyncio.sleep(delay)
                except Exception as e:
                    skipped.append((user_id, username, f"Kick error: {e}"))
                    logger.debug(f'Failed to kick the user \"{username}\" (id: {user_id}, last seen: {last_seen.strftime("%d-%m-%Y %H:%M:%S")}). Reason: \"{e}\"')
        else:
            skipped.append((user_id, username, "Been active"))
            logger.debug(f'Skipped user: \"{username}\" (id: {user_id}). User has satisfyed the activity trashold.')

    return removed, skipped


def parse_duration(text: str) -> timedelta | None:
    pattern = r'(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.fullmatch(pattern, text)
    if not match:
        return None

    weeks, days, hours, minutes, seconds = (int(x) if x else 0 for x in match.groups())
    return timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)



class Handlers:

    @client.on(events.NewMessage(pattern='/start'))
    async def Start(event):
        if not event.is_private:
            return

        user = event.sender_id
        buttons = []

        path = Config.datadir + Config.dialogs
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    dialogs: dict = json.load(f)

                    for title, id in dialogs.items():
                        try:
                            participant = await client(GetParticipantRequest(id, user))
                            if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                                buttons.append(Button.inline(title, data=str(id)))
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f'Failed to read the active-dialog config file!')
            
        if buttons:
            await event.respond(u'Select a channel to manage:', buttons=buttons)
        else:
            await event.respond(u'No shared admin channels found.')
            

    @client.on(events.NewMessage(pattern='^/prune\s+(.+)$'))
    async def Prune(event):
        logger.info(f'Recieved a \"/prune\" request from user with id \"{event.sender_id}\"...')
        arg = event.pattern_match.group(1).strip()
        try:
            trashold = parse_duration(arg)
        except Exception as e:
            logger.error(f'Couldn\'t parse the command input. Error: \"{e}\"')
            await event.reply("Couldn't parse the input. Try a date like `2025-09-15` or duration like `3d2h`.")

        logger.debug(f'Pruning trashold: \"{trashold}\".')

        path = Config.datadir + Config.selections
        try:
            with open(path, 'r') as f:
                selections: dict = json.load(f)

                user = event.sender_id
                channel = selections.get(str(user))
                
                if not channel:
                    await event.respond(u"No channel selected. Use `/start` to select working channel.")
                    return

                removed, skipped = await prune_inactive_users(client, channel, trashold, Config.dry)

                if not removed:
                    await event.respond(f'Not a single user has been offline since \"{trashold}\". Skipped {len(skipped)} participants.')
                    return

                filetext =  f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'
                filetext += f'\n| {'Username':^32} | {'ID':^12} | {'Last Seen':^21} | {'Notes...':<64} |'
                filetext += f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'
                for id, username, last_seen, reason in removed:
                    filetext += f'\n| {f'{username}':^32} | {id:^12} | {last_seen.strftime("%d-%m-%Y %H:%M:%S"):^21} | {reason:<64} |'
                    filetext += f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'

                fremoved = io.BytesIO(filetext.encode('utf-8'))
                fremoved.name = 'removed-users.txt'

                if not skipped:
                    await client.send_file(event.chat_id, file=fremoved, caption=f'Successfully pruned {len(removed)} inactive users!')
                    return
                
                filetext =  f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'
                filetext += f'\n| {'Username':^32} | {'ID':^12} | {'Reason for skip...':<64} |'
                filetext =  f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'
                for id, username, reason in skipped:
                    filetext += f'\n| {f'{username}':^32} | {id:^12} | {reason:<64} |'
                    filetext =  f'\n+-{'':-<32}-+-{'':-<12}-+-{'':-<21}-+-{'':-<64}-+'

                fskipped = io.BytesIO(filetext.encode('utf-8'))
                fskipped.name = 'skipped-users.txt'

                await client.send_file(event.chat_id, [fremoved, fskipped], grouped=True, caption=f'Successfully pruned {len(removed)} inactive users!\nSkipped {len(skipped)} users...')

        except Exception as e:
            logger.error(f'Failed to load user selection: \"{e}\".')
            await event.respond(u"Failed to load selection config.\n\nPlease, try again later.\nContact admin if this error is persistant.")
            return



class Callbacks:

    @client.on(events.CallbackQuery)
    async def Selection(event):
        user    = event.sender_id
        channel = int(event.data.decode())

        path = Config.datadir + Config.selections
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    selections = json.load(f)
                    logger.debug('Loaded user selections table.')
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                selections = { }
        else:
            selections = { }
            logger.debug(f'Created a new selection table with user: \"\"')

        selections[user] = channel

        with open(path, 'w') as f:
            json.dump(selections, f)

        await event.respond(f'Channel selected!\n\nYou can now use commands like `/prune`.')


    @client.on(events.ChatAction)
    async def Invitation(event):
        if event.user_added and event.user_id == (await client.get_me()).id:
            chat = await event.get_chat()
            logger.info(f'Bot was successfully invited to the channel: {chat}')

            path = Config.datadir + Config.dialogs
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        dialogs: dict = json.load(f)
                        logger.debug(f'Succesfully loaded dialog\'s data: {dialogs}')

                        outdated: set = { }
                        for title, id in dialogs.items():
                            try:
                                await client(GetParticipantRequest(id, 'me'))
                                return True
                            except UserNotParticipantError:
                                outdated.add(title)

                        for title in outdated:
                            logger.debug(f'\"{title}\" is an outdated channel. Bot is no longer participant, so it is to be removed from the database!')
                            dialogs.pop(title)

                except Exception as e:
                    logger.error(f"Failed to load active dialog config: \"{e}\"")
                    dialogs = {}
            else:
                dialogs = {}
                logger.debug(f'Initialized new active-dialog file storage with chat \"{chat.title}\", ID: {chat.id}.')

            dialogs[chat.title] = chat.id

            try:
                with open(path, 'w') as f:
                    json.dump(dialogs, f)
                    logger.info(f'Succesfully updated a default database upon joining \"{chat.title}\".')
            except Exception as e:
                logger.error(f'Failed to save active-dialog config file: \"{e}\".')


