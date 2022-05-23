from random import SystemRandom
from string import ascii_letters, digits

from bot import (
    LOGGER,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    ZIP_UNZIP_LIMIT,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import check_storage_threshold, get_base_name
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    sendMarkup,
    sendMessage,
    sendStatusMessage,
)


def add_gd_download(link, listener, is_gdtot):
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if STOP_DUPLICATE and not listener.isLeech:
        LOGGER.info("Checking File/Folder if already in Drive...")
        if listener.isZip:
            gname = name + ".zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except BaseException:
                gname = None
        if gname is not None:
            gmsg, button = GoogleDriveHelper().drive_list(gname, True)
            if gmsg:
                msg = "𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗶𝗻 𝗗𝗿𝗶𝘃𝗲.\𝗻 𝗛𝗲𝗿𝗲 𝗮𝗿𝗲 𝘁𝗵𝗲 𝘀𝗲𝗮𝗿𝗰𝗵 𝗿𝗲𝘀𝘂𝗹𝘁𝘀: "
                return sendMarkup(msg, listener.bot, listener.message, button)
    if any([ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD, TORRENT_DIRECT_LIMIT]):
        arch = any([listener.extract, listener.isZip])
        limit = None
        if STORAGE_THRESHOLD is not None:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f"𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗹𝗲𝗮𝘃𝗲 {STORAGE_THRESHOLD}𝗚𝗕 𝗳𝗿𝗲𝗲 𝘀𝘁𝗼𝗿𝗮𝗴𝗲."
                msg += f"\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}"
                return sendMessage(msg, listener.bot, listener.message)
        if ZIP_UNZIP_LIMIT is not None and arch:
            mssg = f"𝗭𝗶𝗽/𝗨𝗻𝘇𝗶𝗽 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {ZIP_UNZIP_LIMIT}𝗚𝗕"
            limit = ZIP_UNZIP_LIMIT
        elif TORRENT_DIRECT_LIMIT is not None:
            mssg = f"𝗧𝗼𝗿𝗿𝗲𝗻𝘁/𝗗𝗶𝗿𝗲𝗰𝘁 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {TORRENT_DIRECT_LIMIT}𝗚𝗕"
            limit = TORRENT_DIRECT_LIMIT
        if limit is not None:
            LOGGER.info("Checking File/Folder Size...")
            if size > limit * 1024**3:
                msg = (
                    f"{mssg}.\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}."
                )
                return sendMessage(msg, listener.bot, listener.message)
    LOGGER.info(f"Download Name: {name}")
    drive = GoogleDriveHelper(name, listener)
    gid = "".join(SystemRandom().choices(ascii_letters + digits, k=12))
    download_status = GdDownloadStatus(drive, size, listener, gid)
    with download_dict_lock:
        download_dict[listener.uid] = download_status
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)
    drive.download(link)
    if is_gdtot:
        drive.deletefile(link)
