from threading import Thread
from time import sleep

from bot import (
    LOGGER,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    ZIP_UNZIP_LIMIT,
    aria2,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    getDownloadByGid,
    is_magnet,
    new_thread,
)
from bot.helper.ext_utils.fs_utils import check_storage_threshold, get_base_name
from bot.helper.mirror_utils.status_utils.aria_download_status import AriaDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    sendMarkup,
    sendMessage,
    sendStatusMessage,
)


@new_thread
def __onDownloadStarted(api, gid):
    try:
        if any(
            [STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD]
        ):
            download = api.get_download(gid)
            if download.is_metadata:
                LOGGER.info(f"onDownloadStarted: {gid} Metadata")
                return
            elif not download.is_torrent:
                sleep(3)
                download = api.get_download(gid)
            LOGGER.info(f"onDownloadStarted: {gid}")
            dl = getDownloadByGid(gid)
            if not dl:
                return
            if STOP_DUPLICATE and not dl.getListener().isLeech:
                LOGGER.info("Checking File/Folder if already in Drive...")
                sname = download.name
                if dl.getListener().isZip:
                    sname = sname + ".zip"
                elif dl.getListener().extract:
                    try:
                        sname = get_base_name(sname)
                    except BaseException:
                        sname = None
                if sname is not None:
                    smsg, button = GoogleDriveHelper().drive_list(sname, True)
                    if smsg:
                        dl.getListener().onDownloadError(
                            "𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗶𝗻 𝗗𝗿𝗶𝘃𝗲\n\n"
                        )
                        api.remove([download], force=True, files=True)
                        return sendMarkup(
                            "𝗛𝗲𝗿𝗲 𝗮𝗿𝗲 𝘁𝗵𝗲 𝘀𝗲𝗮𝗿𝗰𝗵 𝗿𝗲𝘀𝘂𝗹𝘁𝘀: ",
                            dl.getListener().bot,
                            dl.getListener().message,
                            button,
                        )
            if any([ZIP_UNZIP_LIMIT, TORRENT_DIRECT_LIMIT, STORAGE_THRESHOLD]):
                sleep(1)
                limit = None
                size = download.total_length
                arch = any([dl.getListener().isZip, dl.getListener().extract])
                if STORAGE_THRESHOLD is not None:
                    acpt = check_storage_threshold(size, arch, True)
                    # True if files allocated, if allocation disabled remove
                    # True arg
                    if not acpt:
                        msg = f"𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗹𝗲𝗮𝘃𝗲 {STORAGE_THRESHOLD}𝗚𝗕 𝗳𝗿𝗲𝗲 𝘀𝘁𝗼𝗿𝗮𝗴𝗲."
                        msg += (
                            f"\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}"
                        )
                        dl.getListener().onDownloadError(msg)
                        return api.remove([download], force=True, files=True)
                if ZIP_UNZIP_LIMIT is not None and arch:
                    mssg = f"𝗭𝗶𝗽/𝗨𝗻𝘇𝗶𝗽 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {ZIP_UNZIP_LIMIT}𝗚𝗕"
                    limit = ZIP_UNZIP_LIMIT
                elif TORRENT_DIRECT_LIMIT is not None:
                    mssg = f"𝗧𝗼𝗿𝗿𝗲𝗻𝘁/𝗗𝗶𝗿𝗲𝗰𝘁 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {TORRENT_DIRECT_LIMIT}𝗚𝗕"
                    limit = TORRENT_DIRECT_LIMIT
                if limit is not None:
                    LOGGER.info("Checking File/Folder Size...")
                    if size > limit * 1024**3:
                        dl.getListener().onDownloadError(
                            f"{mssg}.\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}"
                        )
                        return api.remove([download], force=True, files=True)
    except Exception as e:
        LOGGER.error(
            f"{e} onDownloadStart: {gid} stop duplicate and size check didn't pass"
        )


@new_thread
def __onDownloadComplete(api, gid):
    LOGGER.info(f"onDownloadComplete: {gid}")
    dl = getDownloadByGid(gid)
    download = api.get_download(gid)
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f"Changed gid from {gid} to {new_gid}")
    elif dl:
        Thread(target=dl.getListener().onDownloadComplete).start()


@new_thread
def __onDownloadStopped(api, gid):
    sleep(6)
    if dl := getDownloadByGid(gid):
        dl.getListener().onDownloadError("★ 𝗠𝗔𝗚𝗡𝗘𝗧/𝗧𝗢𝗥𝗥𝗘𝗡𝗧 𝗟𝗜𝗡𝗞 𝗜𝗦 𝗗𝗘𝗔𝗗 ❌ ★")


@new_thread
def __onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    sleep(0.5)
    dl = getDownloadByGid(gid)
    try:
        download = api.get_download(gid)
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    except Exception:
        pass
    if dl:
        dl.getListener().onDownloadError(error)


def start_listener():
    aria2.listen_to_notifications(
        threaded=True,
        on_download_start=__onDownloadStarted,
        on_download_error=__onDownloadError,
        on_download_stop=__onDownloadStopped,
        on_download_complete=__onDownloadComplete,
        timeout=20,
    )


def add_aria2c_download(link: str, path, listener, filename, auth):
    if is_magnet(link):
        download = aria2.add_magnet(link, {"dir": path})
    else:
        download = aria2.add_uris(
            [link], {"dir": path, "out": filename, "header": f"authorization: {auth}"}
        )
    if download.error_message:
        error = str(download.error_message).replace("<", " ").replace(">", " ")
        LOGGER.info(f"Download Error: {error}")
        return sendMessage(error, listener.bot, listener.message)
    with download_dict_lock:
        download_dict[listener.uid] = AriaDownloadStatus(download.gid, listener)
        LOGGER.info(f"Started: {download.gid} DIR: {download.dir} ")
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)


start_listener()
