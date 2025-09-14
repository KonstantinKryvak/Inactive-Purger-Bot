

import logging


from dotenv import load_dotenv
load_dotenv()


try:
    logging.basicConfig(
        format   ='%(asctime)s [%(levelname)s] %(message)s',
        level    =logging.INFO,
        handlers =[ logging.FileHandler('session.log'), logging.StreamHandler() ]
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


