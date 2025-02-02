from speedtest import Speedtest
from telegram.ext import CommandHandler

from bot import dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


def speedtest(update, context):
    speed = sendMessage("𝐑𝐮𝐧𝐧𝐢𝐧𝐠 𝐒𝐩𝐞𝐞𝐝 𝐓𝐞𝐬𝐭 . . . ", context.bot, update.message)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    string_speed = f"""
╭───🛰️ 𝐒𝐞𝐫𝐯𝐞𝐫 🛰️
├ 🖥️ 𝐍𝐚𝐦𝐞 ⇢ <code>{result['server']['name']}</code>
├ 🌍 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⇢ <code>{result['server']['country']}, {result['server']['cc']}</code>
├ 🪂 𝐒𝐩𝐨𝐧𝐬𝐨𝐫 ⇢ <code>{result['server']['sponsor']}</code>
├ 🤖 𝐈𝐒𝐏 ⇢ <code>{result['client']['isp']}</code>
│
├ 🎯 𝐒𝐩𝐞𝐞𝐝𝐓𝐞𝐬𝐭 𝐑𝐞𝐬𝐮𝐥𝐭𝐬 🎯
├ 📤 𝐔𝐩𝐥𝐨𝐚𝐝 ⇢ <code>{speed_convert(result['upload'] / 8)}</code>
├ 📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 ⇢ <code>{speed_convert(result['download'] / 8)}</code>
├ 📊 𝐏𝐢𝐧𝐠 ⇢ <code>{result['ping']} ms</code>
╰──🔗 𝐈𝐒𝐏 𝐑𝐚𝐭𝐢𝐧𝐠 ⇢ <code>{result['client']['isprating']}</code>
"""
    editMessage(string_speed, speed)


def speed_convert(size):
    """Hi human, you can't read bytes?"""
    power = 2**10
    zero = 0
    units = {0: "", 1: "Kb/s", 2: "MB/s", 3: "Gb/s", 4: "Tb/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"


SPEED_HANDLER = CommandHandler(
    BotCommands.SpeedCommand,
    speedtest,
    filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
    run_async=True,
)

dispatcher.add_handler(SPEED_HANDLER)
