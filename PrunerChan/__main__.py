

from dotenv  import load_dotenv
from logging import basicConfig, INFO, FileHandler, StreamHandler

load_dotenv()


try:
    basicConfig(
        format   = '%(asctime)s [%(levelname)s] %(message)s',
        level    = INFO,
        handlers = [FileHandler('session.log'), StreamHandler()]
    )


    from os          import environ as env
    from .connection import Client
    from .interface  import *

    Client.Account.start(bot_token=env['bot-token'])

    Client.Interface.add_handler(CommandHandler('start',    Callbacks.StartCommand))
    Client.Interface.add_handler(CommandHandler('schedule', Callbacks.RegisterCommand))
    Client.Interface.add_handler(CommandHandler('prune',    Callbacks.PruneTrigerCommand))

    for chat_id, config in Registered.items():
        Scheduler.add_job(logic.DoPrune, 'interval', hours=config['timeout'], args=[chat_id, config['threshold']], id=chat_id, replace_existing=True)


    from asyncio import get_event_loop
    loop = get_event_loop()
    loop.call_soon_threadsafe(Scheduler.start)

    Client.Interface.run_polling()


except Exception as error:
    print(f'Exception catched: \"{str(error)}\", of type \"{type(error).__name__}\"')


