

from dotenv import load_dotenv
load_dotenv()


from sys       import argv
from .backends import Config, client, logger


if '--dry' in argv:
    Config.dry = True
    logger.warning('Running in dry mode... No removal request will be send...')


try:
    client.run_until_disconnected()


except Exception as error:
    print(f'Exception catched: \"{str(error)}\", of type \"{type(error).__name__}\"')




#    for chat_id, config in Registered.items():
#        Scheduler.add_job(logic.DoPrune, 'interval', hours=config['timeout'], args=[chat_id, config['threshold']], id=chat_id, replace_existing=True)


#    from asyncio import get_event_loop
#    loop = get_event_loop()
#    loop.call_soon_threadsafe(Scheduler.start)
