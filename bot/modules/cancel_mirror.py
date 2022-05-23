from time import sleep

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    OWNER_ID,
    QB_SEED,
    SUDO_USERS,
    dispatcher,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    MirrorStatus,
    getAllDownload,
    getDownloadByGid,
)
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMarkup, sendMessage


def cancel_mirror(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    user_id = update.message.from_user.id
    if len(args) > 1:
        gid = args[1]
        dl = getDownloadByGid(gid)
        if not dl:
            mirror_message = dl.message
            sendMessage(
                f"𝗚𝗜𝗗 ⇢ <code>{gid}</code> 𝐍𝐨𝐭 𝐅𝐨𝐮𝐧𝐝.", context.bot, update.message
            )
            return
    elif update.message.reply_to_message:
        mirror_message = update.message.reply_to_message
        with download_dict_lock:
            list(download_dict.keys())
            try:
                dl = download_dict[mirror_message.message_id]
            except Exception:
                dl = None
        if not dl:
            return sendMessage(
                "This is not an active task!", context.bot, update.message
            )
    elif len(args) == 1:
        msg = f"𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮𝗰𝘁𝗶𝘃𝗲 <code>/{BotCommands.MirrorCommand}</code> 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝘄𝗵𝗶𝗰𝗵 𝘄𝗮𝘀 𝘂𝘀𝗲𝗱 𝘁𝗼 𝘀𝘁𝗮𝗿𝘁 𝘁𝗵𝗲 𝗱𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗼𝗿 𝘀𝗲𝗻𝗱 <code>/{BotCommands.CancelMirror} GID</code> to cancel it!"
        return sendMessage(msg, context.bot, update.message)

    if (
        OWNER_ID != user_id
        and dl.message.from_user.id != user_id
        and user_id not in SUDO_USERS
    ):
        return sendMessage("This task is not for you!", context.bot, update.message)

    if dl.status() == MirrorStatus.STATUS_ARCHIVING:
        sendMessage(
            "𝐀𝐫𝐜𝐡𝐢𝐯𝐚𝐥 𝐢𝐧 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬, 𝐘𝐨𝐮 𝐂𝐚𝐧'𝐭 𝐂𝐚𝐧𝐜𝐞𝐥 𝐈𝐭.", context.bot, update.message
        )
    elif dl.status() == MirrorStatus.STATUS_EXTRACTING:
        sendMessage(
            "𝐄𝐱𝐭𝐫𝐚𝐜𝐭 𝐢𝐧 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬, 𝐘𝐨𝐮 𝐂𝐚𝐧'𝐭 𝐂𝐚𝐧𝐜𝐞𝐥 𝐈𝐭.", context.bot, update.message
        )
    elif dl.status() == MirrorStatus.STATUS_SPLITTING:
        sendMessage(
            "𝗦𝗽𝗹𝗶𝘁 𝐢𝐧 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬, 𝐘𝐨𝐮 𝐂𝐚𝐧'𝐭 𝐂𝐚𝐧𝐜𝐞𝐥 𝐈𝐭.", context.bot, update.message
        )
    else:
        dl.download().cancel_download()


def cancel_all(status):
    gid = ""
    while True:
        dl = getAllDownload(status)
        if dl:
            if dl.gid() != gid:
                gid = dl.gid()
                dl.download().cancel_download()
                sleep(1)
        else:
            break


def cancell_all_buttons(update, context):
    buttons = button_build.ButtonMaker()
    buttons.sbutton("𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴", "canall down")
    buttons.sbutton("Uploading", "canall up")
    if QB_SEED:
        buttons.sbutton("𝗨𝗽𝗹𝗼𝗮𝗱𝗶𝗻𝗴", "canall seed")
    buttons.sbutton("𝗖𝗹𝗼𝗻𝗶𝗻𝗴", "canall clone")
    buttons.sbutton("𝗔𝗹𝗹", "canall all")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup("𝗖𝗵𝗼𝗼𝘀𝗲 𝘁𝗮𝘀𝗸𝘀 𝘁𝗼 𝗰𝗮𝗻𝗰𝗲𝗹: ", context.bot, update.message, button)


def cancel_all_update(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(" ")
    if CustomFilters._owner_query(user_id):
        query.answer()
        query.message.delete()
        cancel_all(data[1])
    else:
        query.answer(
            text="You don't have permission to use these buttons!", show_alert=True
        )


cancel_mirror_handler = CommandHandler(
    BotCommands.CancelMirror,
    cancel_mirror,
    filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user),
    run_async=True,
)

cancel_all_handler = CommandHandler(
    BotCommands.CancelAllCommand,
    cancell_all_buttons,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)

cancel_all_buttons_handler = CallbackQueryHandler(
    cancel_all_update, pattern="canall", run_async=True
)

dispatcher.add_handler(cancel_all_handler)
dispatcher.add_handler(cancel_mirror_handler)
dispatcher.add_handler(cancel_all_buttons_handler)
