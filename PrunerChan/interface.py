

from .            import logic, utils
from .connection  import Client
from logging      import getLogger
from telegram     import Update
from telegram.ext import CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler


__log__      = getLogger(__name__)
Scheduler  = AsyncIOScheduler()
Registered = { }


class Callbacks:

    async def StartCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bot is running. Use /register {threshold} {timeout} to enable auto-prune.")
        __log__.info(f"/start from {update.effective_user.id}")

    
    async def RegisterCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chatID = update.effective_chat.id
            threshold = int(context.args[0])
            timeout = int(context.args[1])
            Registered[chatID] = {'threshold': threshold, 'timeout': timeout}
            utils.SaveRegisteredChats(Registered)
            Scheduler.add_job(logic.DoPrune, 'interval', hours=timeout, args=[chatID, threshold], id=str(chatID), replace_existing=True)
            __log__.info(f"Registered chat {chatID} with threshold={threshold}, timeout={timeout}")
        except (IndexError, ValueError):
            __log__.warning(f"Invalid /register args from {update.effective_user.id}")


    async def PruneTrigerCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        config = Registered.get(chat_id)
        if not config:
            await update.message.reply_text("This chat is not registered. Use /register first.")
            return
        __log__.info("Starting manual prune...")
        await logic.DoPrune(chat_id, config['threshold'])
        __log__.info("Manual prune complete.")


