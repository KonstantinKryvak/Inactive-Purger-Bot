

from telegram.ext import ApplicationBuilder
from telethon     import TelegramClient

from os           import environ as env


class Client:
    Interface = ApplicationBuilder().token(env['bot-token']).build()
    Account   = TelegramClient('anon', env['api-ID'], env['api-hash'])


