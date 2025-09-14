

import logging, json, os



logger = logging.getLogger(__name__)

def LoadRegisteredChats():
    cfgfile = 'registrations.json'
    if os.path.exists(''):
        try:
            with open(cfgfile, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    return {}


def SaveRegisteredChats(registered: dict):
    try:
        with open('registrations.json', 'w') as f:
            json.dump(registered, f)
        logger.debug("Saved registered chats to file.")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


