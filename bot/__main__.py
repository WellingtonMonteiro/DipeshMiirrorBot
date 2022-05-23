from signal import signal, SIGINT
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from threading import Thread
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from pyrogram import idle
from sys import executable
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler
from datetime import datetime
import pytz

from bot import bot, app, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, alive, LOGGER, Interval, rss_session, INCOMPLETE_TASK_NOTIFIER, DB_URI, CHANNEL_USERNAME, TIMEZONE
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import auto_delete_message, sendMessage, sendMarkup, editMessage, sendLogFile
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker

from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, count, leech_settings, search, rss, usage, speedtest

now = datetime.now(pytz.timezone(f'{TIMEZONE}'))


def stats(update, context):
    if ospath.exists('.git'):
        last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'"], shell=True).decode()
        botVersion = check_output(["git log -1 --date=format:v%y.%m%d.%H%M --pretty=format:%cd"], shell=True).decode()
    else:
        last_commit = 'No UPSTREAM_REPO'
        botVersion = 'v1'
    currentTime = get_readable_time(time() - botStartTime)
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)
    stats = f'╭───《🌐 𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 🌐》\n│\n'\
            f'├─🔢 𝗖𝗼𝗺𝗺𝗶𝘁 𝗗𝗮𝘁𝗲 ⇢ {last_commit} \n'\
            f'├─🔢 𝗩𝗲𝗿𝘀𝗶𝗼𝗻 ⇢ {botVersion}\n'\
            f'├─🤖 𝗕𝗼𝘁 𝗨𝗽𝘁𝗶𝗺𝗲 ⇢ {currentTime}\n│\n'\
            f'├─✨ 𝗢𝗦 𝗨𝗽𝘁𝗶𝗺𝗲⇢ {osUptime}\n' \
            f'├─💽 𝗧𝗼𝘁𝗮𝗹 𝗗𝗶𝘀𝗸 𝗦𝗽𝗮𝗰𝗲 ⇢ {total}\n'\
            f'├─💻 𝗨𝘀𝗲𝗱 ⇢ {used} | 💾 𝗙𝗿𝗲𝗲 ⇢ {free}\n│\n'\
            f'├─📤 𝗨𝗽𝗹𝗼𝗮𝗱 ⇢ {sent}\n'\
            f'├─📥 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 ⇢ {recv}\n│\n'\
            f'├─🖥️ 𝗖𝗣𝗨 ⇢ {cpuUsage}%\n'\
            f'├─📏 𝗥𝗔𝗠 ⇢ {mem_p}%\n'\
            f'├─💿 𝗗𝗜𝗦𝗞 ⇢ {disk}%\n'\
            f'├─🛰️ 𝗣𝗵𝘆𝘀𝗶𝗰𝗮𝗹 𝗖𝗼𝗿𝗲𝘀 ⇢ {p_core}\n'\
            f'├─⚙️ 𝗧𝗼𝘁𝗮𝗹 𝗖𝗼𝗿𝗲𝘀 ⇢ {t_core}\n'\
            f'├─⚡ 𝗦𝗪𝗔𝗣 ⇢ {swap_t} | 𝗨𝘀𝗲𝗱 ⇢ {swap_p}%\n│\n'\
            f'├─💽 𝗠𝗲𝗺𝗼𝗿𝘆 𝗧𝗼𝘁𝗮𝗹 ⇢ {mem_t}\n'\
            f'├─💾 𝗠𝗲𝗺𝗼𝗿𝘆 𝗙𝗿𝗲𝗲 ⇢ {mem_a}\n'\
            f'├─💻 𝗠𝗲𝗺𝗼𝗿𝘆 𝗨𝘀𝗲𝗱 ⇢ {mem_u}\n│\n'\
            f'╰───《☣️ <b>👿 @DipeshMirror</b> ☣️》\n'
    sendMessage(stats, context.bot, update.message)

def start(update, context):
    chat_u = CHANNEL_USERNAME.replace('@','')
    buttons = ButtonMaker()
    buttons.buildbutton("👉🏻 𝗠𝗜𝗥𝗥𝗢𝗥 𝗚𝗥𝗢𝗨𝗣 👈🏻", f"https://t.me/{chat_u}")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = ' 𝗧𝗵𝗶𝘀 𝗯𝗼𝘁 𝗰𝗮𝗻 𝗺𝗶𝗿𝗿𝗼𝗿 𝗮𝗹𝗹 𝘆𝗼𝘂𝗿 𝗹𝗶𝗻𝗸𝘀 𝘁𝗼 𝗚𝗼𝗼𝗴𝗹𝗲 𝗗𝗿𝗶𝘃𝗲!'
        start_string += f'\n\n 𝗧𝘆𝗽𝗲 /{BotCommands.HelpCommand} 𝘁𝗼 𝗴𝗲𝘁 𝗮 𝗹𝗶𝘀𝘁 𝗼𝗳 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗰𝗼𝗺𝗺𝗮𝗻𝗱𝘀.'
        reply_message = sendMarkup(start_string, context.bot, update.message, reply_markup)
    else:
        reply_message = sendMarkup(f'𝗗𝗲𝗮𝗿 {update.message.chat.first_name} ({update.message.chat.username}), \n\n\n 𝗜𝗳 𝗬𝗼𝘂 𝗪𝗮𝗻𝘁 𝗧𝗼 𝗨𝘀𝗲 𝗠𝗲, 𝗬𝗼𝘂 𝗛𝗮𝘃𝗲 𝗧𝗼 𝗝𝗼𝗶𝗻 𝗠𝘆 𝗠𝗶𝗿𝗿𝗼𝗿 𝗚𝗿𝗼𝘂𝗽 𝗕𝘆 𝗖𝗹𝗶𝗰𝗸𝗶𝗻𝗴 𝗧𝗵𝗲 𝗕𝗲𝗹𝗼𝘄 𝗕𝘂𝘁𝘁𝗼𝗻.', context.bot, update.message, reply_markup)
    Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()


def restart(update, context):
    restart_message = sendMessage("𝐁𝐨𝐭 𝐈𝐬 𝐑𝐞𝐬𝐭𝐚𝐫𝐭𝐢𝐧𝐠..🔧", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
    if Interval:
        Interval[0].cancel()
    alive.kill()
    clean_all()
    srun(["pkill", "-f", "gunicorn|aria2c|qbittorrent-nox|megasdkrest"])
    srun(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("⛔ 𝗦𝘁𝗮𝗿𝘁𝗶𝗻𝗴 𝗣𝗶𝗻𝗴", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} 𝗺𝘀', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)

help_string_telegraph = f'''<br>
<b>/{BotCommands.HelpCommand}</b>: To get this message
<br><br>
<b>/{BotCommands.MirrorCommand}</b> [download_url][magnet_link]: Start mirroring to Google Drive. Send <b>/{BotCommands.MirrorCommand}</b> for more help
<br><br>
<b>/{BotCommands.ZipMirrorCommand}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.UnzipMirrorCommand}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.QbMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start Mirroring using qBittorrent, Use <b>/{BotCommands.QbMirrorCommand} s</b> to select files before downloading
<br><br>
<b>/{BotCommands.QbZipMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.QbUnzipMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.LeechCommand}</b> [download_url][magnet_link]: Start leeching to Telegram, Use <b>/{BotCommands.LeechCommand} s</b> to select files before leeching
<br><br>
<b>/{BotCommands.ZipLeechCommand}</b> [download_url][magnet_link]: Start leeching to Telegram and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.UnzipLeechCommand}</b> [download_url][magnet_link][torent_file]: Start leeching to Telegram and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.QbLeechCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent, Use <b>/{BotCommands.QbLeechCommand} s</b> to select files before leeching
<br><br>
<b>/{BotCommands.QbZipLeechCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.QbUnzipLeechCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.CloneCommand}</b> [drive_url][gdtot_url]: Copy file/folder to Google Drive
<br><br>
<b>/{BotCommands.CountCommand}</b> [drive_url][gdtot_url]: Count file/folder of Google Drive
<br><br>
<b>/{BotCommands.DeleteCommand}</b> [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo)
<br><br>
<b>/{BotCommands.WatchCommand}</b> [yt-dlp supported link]: Mirror yt-dlp supported link. Send <b>/{BotCommands.WatchCommand}</b> for more help
<br><br>
<b>/{BotCommands.ZipWatchCommand}</b> [yt-dlp supported link]: Mirror yt-dlp supported link as zip
<br><br>
<b>/{BotCommands.LeechWatchCommand}</b> [yt-dlp supported link]: Leech yt-dlp supported link
<br><br>
<b>/{BotCommands.LeechZipWatchCommand}</b> [yt-dlp supported link]: Leech yt-dlp supported link as zip
<br><br>
<b>/{BotCommands.LeechSetCommand}</b>: Leech settings
<br><br>
<b>/{BotCommands.SetThumbCommand}</b>: Reply photo to set it as Thumbnail
<br><br>
<b>/{BotCommands.RssListCommand}</b>: List all subscribed rss feed info
<br><br>
<b>/{BotCommands.RssGetCommand}</b>: [Title] [Number](last N links): Force fetch last N links
<br><br>
<b>/{BotCommands.RssSubCommand}</b>: [Title] [Rss Link] f: [filter]: Subscribe new rss feed
<br><br>
<b>/{BotCommands.RssUnSubCommand}</b>: [Title]: Unubscribe rss feed by title
<br><br>
<b>/{BotCommands.RssSettingsCommand}</b>: Rss Settings
<br><br>
<b>/{BotCommands.CancelMirror}</b>: Reply to the message by which the download was initiated and that download will be cancelled
<br><br>
<b>/{BotCommands.CancelAllCommand}</b>: Cancel all downloading tasks
<br><br>
<b>/{BotCommands.ListCommand}</b> [query]: Search in Google Drive(s)
<br><br>
<b>/{BotCommands.SearchCommand}</b> [query]: Search for torrents with API
<br>sites: <code>rarbg, 1337x, yts, etzv, tgx, torlock, piratebay, nyaasi, ettv</code><br><br>
<b>/{BotCommands.StatusCommand}</b>: Shows a status of all the downloads
<br><br>
<b>/{BotCommands.StatsCommand}</b>: Show Stats of the machine the bot is hosted on
<br><br>
<b>/{BotCommands.UsageCommand}</b>: Show heroku dyno usage (Owner Only)
'''

help = telegraph.create_page(
        title='👿 Dipesh Mirror Bot Help',
        content=help_string_telegraph,
    )["path"]

help_string = f'''
/{BotCommands.MirrorCommand}: Start mirroring the link to Google Drive. 
/{BotCommands.QbMirrorCommand}: Start Mirroring using qBittorrent, Use /{BotCommands.QbMirrorCommand} s to select files before downloading
/{BotCommands.ZipMirrorCommand}: Start mirroring and upload the archived (.zip) version of the download
/{BotCommands.UnzipMirrorCommand}: Starts mirroring and if downloaded file is any archive, extracts it to Google Drive
/{BotCommands.QbZipMirrorCommand}: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension
/{BotCommands.QbUnzipMirrorCommand}: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension
/{BotCommands.LeechCommand}: Start leeching to Telegram, Use /{BotCommands.LeechCommand} s to select files before leeching
/{BotCommands.ZipLeechCommand}: Start leeching to Telegram and upload the file/folder compressed with zip extension
/{BotCommands.UnzipLeechCommand}: Start leeching to Telegram and upload the file/folder extracted from any archive extension
/{BotCommands.QbLeechCommand}: Start leeching to Telegram using qBittorrent, Use /{BotCommands.QbLeechCommand} s to select files before leeching
/{BotCommands.QbZipLeechCommand}: Start leeching to Telegram using qBittorrent and upload the file/folder compressed with zip extension
/{BotCommands.QbUnzipLeechCommand}: Start leeching to Telegram using qBittorrent and upload the file/folder extracted from any archive extension
/{BotCommands.CloneCommand}: Copy file/folder to Google Drive
/{BotCommands.ListCommand}: Searches the search term in the Google Drive
/{BotCommands.SearchCommand}: Search for torrents with API. 
'''

def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("🤖 𝗢𝗧𝗛𝗘𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 🤖", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update.message, reply_markup)

botcmds = [

        (f'{BotCommands.StartCommand}', 'Check if bot is alive or not'),
        (f'{BotCommands.MirrorCommand}', 'Mirror'),
        (f'{BotCommands.ZipMirrorCommand}','Mirror and upload as zip'),
        (f'{BotCommands.UnzipMirrorCommand}','Mirror and extract files'),
        (f'{BotCommands.CancelMirror}','Cancel a task'),
        (f'{BotCommands.CancelAllCommand}','Cancel all downloading tasks'),
        (f'{BotCommands.ListCommand}','Search files in Drive'),
        (f'{BotCommands.SearchCommand}',' Search for torrents with API'),
        (f'{BotCommands.StatusCommand}','Get Mirror Status message'),
        (f'{BotCommands.UsageCommand}', 'Check Heroku Dyno Usage'),
        (f'{BotCommands.AuthorizedUsersCommand}','Get list of Authorized Chats and Sudo Users '),
        (f'{BotCommands.AuthorizeCommand}','Authorize a user/chat'),
        (f'{BotCommands.UnAuthorizeCommand}','Unauthorize a user/chat'),
        (f'{BotCommands.AddSudoCommand}','Add a sudo user'),
        (f'{BotCommands.RmSudoCommand}',' Remove a sudo use'),
        (f'{BotCommands.PingCommand}','Ping the bot'),
        (f'{BotCommands.RestartCommand}','Restart the bot'),
        (f'{BotCommands.StatsCommand}','Bot usage stats'),
        (f'{BotCommands.HelpCommand}','Get detailed help'),
        (f'{BotCommands.LogCommand}','Get the bot Log'),
        (f'{BotCommands.SpeedCommand}','Speedtest Server'),
        (f'{BotCommands.CloneCommand}','Copy file/folder to Drive'),
        (f'{BotCommands.CountCommand}','Count file/folder of Drive'),
        (f'{BotCommands.WatchCommand}','Mirror yt-dlp supported link'),
        (f'{BotCommands.ZipWatchCommand}','Mirror yt-dlp supported link as zip'),
        (f'{BotCommands.QbMirrorCommand}','Mirror torrent using qBittorrent'),
        (f'{BotCommands.QbZipMirrorCommand}','Mirror torrent and upload as zip using qb'),
        (f'{BotCommands.QbUnzipMirrorCommand}','Mirror torrent and extract files using qb'),
        (f'{BotCommands.DeleteCommand}','Delete file/folder from Drive'),
        (f'{BotCommands.ShellCommand}','Run commands in Shell'),
#        (f'{BotCommands.ExecHelpCommand}','Executor'),
        (f'{BotCommands.LeechSetCommand}','Leech settings'),
        (f'{BotCommands.SetThumbCommand}','Set thumbnail'),
        (f'{BotCommands.LeechCommand}','Leech'),
        (f'{BotCommands.ZipLeechCommand}','Leech and upload as zip'),
        (f'{BotCommands.UnzipLeechCommand}','Leech and extract files'),
        (f'{BotCommands.QbLeechCommand}','Leech torrent using qBittorrent'),
        (f'{BotCommands.QbZipLeechCommand}','Leech torrent and upload as zip using qb'),
        (f'{BotCommands.QbUnzipLeechCommand}','Leech torrent and extract using qb'),
        (f'{BotCommands.LeechWatchCommand}','Leech yt-dlp supported link'),
        (f'{BotCommands.LeechZipWatchCommand}','Leech yt-dlp supported link as zip'),
        (f'{BotCommands.AddleechlogCommand}','Add Leech Log'),
        (f'{BotCommands.RmleechlogCommand}','Remove Leech Log'),
        (f'{BotCommands.AddleechlogaltCommand}','Add Alternate Leech Logs'),
        (f'{BotCommands.RmleechlogaltCommand}','Remove More Leech Logs'),
#        (f'{BotCommands.RssListCommand}','List all subscribed rss feed info'),
#        (f'{BotCommands.RssGetCommand}','Force fetch links'),
#        (f'{BotCommands.RssSubCommand}','Subscribe new rss feed'),
#        (f'{BotCommands.RssUnSubCommand}','Unubscribe rss feed by title'),
#        (f'{BotCommands.RssSettingsCommand}','Rss Settings')
         
    ]

def main():
    start_cleanup()
    # Check if the bot is restarting
    kie = datetime.now(pytz.timezone(f'{TIMEZONE}'))
    jam = kie.strftime('\n 𝗗𝗮𝘁𝗲 : %d/%m/%Y\n 𝗧𝗶𝗺𝗲: %I:%M:%S %P')
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        notifier_dict = DbManger().get_incomplete_tasks()
        if notifier_dict:
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = f"𝐁𝐎𝐓 𝐆𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n {jam}\n\n 𝗧𝗶𝗺𝗲 𝗭𝗼𝗻𝗲 : {TIMEZONE}\n\n𝐑𝐞-𝐌𝐢𝐫𝐫𝐨𝐫 𝐘𝐨𝐮'𝐫 𝐓𝐡𝐢𝐧𝐠'𝐬!"
                else:
                    msg = f"𝐁𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n {jam}\n\n 𝗧𝗶𝗺𝗲 𝗭𝗼𝗻𝗲 : {TIMEZONE}\n\n𝐑𝐞-𝐌𝐢𝐫𝐫𝐨𝐫 𝐘𝐨𝐮'𝐫 𝐓𝐡𝐢𝐧𝐠'𝐬!"
                for tag, links in data.items():
                     msg += f"\n\n{tag}: "
                     for index, link in enumerate(links, start=1):
                         msg += f" <a href='{link}'>{index}</a> |"
                         if len(msg.encode()) > 4000:
                             if '𝐁𝐎𝐓 𝐆𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃' in msg and cid == chat_id:
                                 bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl')
                                 osremove(".restartmsg")
                             else:
                                 bot.sendMessage(cid, msg, 'HTML')
                             msg = ''
                if '𝐁𝐎𝐓 𝐆𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃' in msg and cid == chat_id:
                     bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl')
                     osremove(".restartmsg")
                else:
                    bot.sendMessage(cid, msg, 'HTML')

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text(f"𝐁𝐎𝐓 𝐆𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n {jam}\n\n 𝗧𝗶𝗺𝗲 𝗭𝗼𝗻𝗲 : {TIMEZONE}\n\n𝐑𝐞-𝐌𝐢𝐫𝐫𝐨𝐫 𝐘𝐨𝐮'𝐫 𝐓𝐡𝐢𝐧𝐠'𝐬", chat_id, msg_id)
        osremove(".restartmsg")

    bot.set_my_commands(botcmds)
    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    usage_handler = CommandHandler(BotCommands.UsageCommand, usage, filters=CustomFilters.owner_filter, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    dispatcher.add_handler(usage_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)
    if rss_session is not None:
        rss_session.start()

app.start()
main()
idle()
