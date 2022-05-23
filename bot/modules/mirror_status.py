from threading import Thread
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    DOWNLOAD_DIR,
    botStartTime,
    dispatcher,
    download_dict,
    download_dict_lock,
    status_reply_dict,
    status_reply_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    turn,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    sendMessage,
    sendStatusMessage,
    update_all_messages,
)


def mirror_status(update, context):
    with download_dict_lock:
        if len(download_dict) == 0:
            currentTime = get_readable_time(time() - botStartTime)
            free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
            message = "𝐍𝐨 𝐚𝐜𝐭𝐢𝐯𝐞 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐬!\n___________________________"
            message += (
                f"\n🖥️ 𝗖𝗣𝗨 ⇢ {cpu_percent()}% | 🗄️ 𝗙𝗥𝗘𝗘 ⇢ {free}"
                f"\n💾 𝗥𝗔𝗠 ⇢ {virtual_memory().percent}% | ⏳ 𝗨𝗣𝗧𝗜𝗠𝗘 ⇢ {currentTime}"
            )
            reply_message = sendMessage(message, context.bot, update.message)
            Thread(
                target=auto_delete_message,
                args=(context.bot, update.message, reply_message),
            ).start()
            return
    index = update.effective_chat.id
    with status_reply_dict_lock:
        if index in status_reply_dict.keys():
            deleteMessage(context.bot, status_reply_dict[index])
            del status_reply_dict[index]
    sendStatusMessage(update.message, context.bot)
    deleteMessage(context.bot, update.message)


def status_pages(update, context):
    query = update.callback_query
    data = query.data
    data = data.split(" ")
    query.answer()
    done = turn(data)
    if done:
        update_all_messages()
    else:
        query.message.delete()


mirror_status_handler = CommandHandler(
    BotCommands.StatusCommand,
    mirror_status,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)

status_pages_handler = CallbackQueryHandler(
    status_pages, pattern="status", run_async=True
)
dispatcher.add_handler(mirror_status_handler)
dispatcher.add_handler(status_pages_handler)
