# from hashlib import sha256, sha1
# from base64 import b16encode, b32decode
# from bencoding import bencode, bdecode
from os import listdir
from os import path as ospath
from time import sleep, time

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from bot import (
    BASE_URL,
    LOGGER,
    QB_SEED,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    TORRENT_TIMEOUT,
    WEB_PINCODE,
    ZIP_UNZIP_LIMIT,
    dispatcher,
    download_dict,
    download_dict_lock,
    get_client,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    getDownloadByGid,
    setInterval,
)
from bot.helper.ext_utils.fs_utils import (
    check_storage_threshold,
    clean_unwanted,
    get_base_name,
)
from bot.helper.mirror_utils.status_utils.qbit_download_status import QbDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.message_utils import (
    deleteMessage,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
    update_all_messages,
)


class QbDownloader:
    POLLING_INTERVAL = 3

    def __init__(self, listener):
        self.__listener = listener
        self.__path = ""
        self.__name = ""
        self.select = False
        self.client = None
        self.periodic = None
        self.ext_hash = ""
        self.__stalled_time = time()
        self.__uploaded = False
        self.__seeding = False
        self.__sizeChecked = False
        self.__dupChecked = False
        self.__rechecked = False

    def add_qb_torrent(self, link, path, select):
        self.__path = path
        self.select = select
        self.client = get_client()
        try:
            op = self.client.torrents_add(
                link,
                save_path=path,
                tags=self.__listener.uid,
                headers={"user-agent": "Wget/1.12"},
            )
            sleep(0.3)
            if op.lower() == "ok.":
                tor_info = self.client.torrents_info(tag=self.__listener.uid)
                if len(tor_info) == 0:
                    while True:
                        tor_info = self.client.torrents_info(tag=self.__listener.uid)
                        if len(tor_info) > 0:
                            break
                        elif time() - self.__stalled_time >= 12:
                            msg = "This Torrent already added or not a torrent. If something wrong please report."
                            sendMessage(
                                msg, self.__listener.bot, self.__listener.message
                            )
                            self.client.auth_log_out()
                            return
            else:
                sendMessage(
                    "This is an unsupported/invalid link.",
                    self.__listener.bot,
                    self.__listener.message,
                )
                self.client.auth_log_out()
                return
            tor_info = tor_info[0]
            self.__name = tor_info.name
            self.ext_hash = tor_info.hash
            with download_dict_lock:
                download_dict[self.__listener.uid] = QbDownloadStatus(
                    self.__listener, self
                )
            self.__listener.onDownloadStart()
            LOGGER.info(f"QbitDownload started: {self.__name} - Hash: {self.ext_hash}")
            self.periodic = setInterval(self.POLLING_INTERVAL, self.__qb_listener)
            if BASE_URL is not None and select:
                if link.startswith("magnet:"):
                    metamsg = "Downloading Metadata, wait then you can select files or mirror torrent file"
                    meta = sendMessage(
                        metamsg, self.__listener.bot, self.__listener.message
                    )
                    while True:
                        tor_info = self.client.torrents_info(
                            torrent_hashes=self.ext_hash
                        )
                        if len(tor_info) == 0:
                            return deleteMessage(self.__listener.bot, meta)
                        try:
                            tor_info = tor_info[0]
                            if tor_info.state not in [
                                "metaDL",
                                "checkingResumeData",
                                "pausedDL",
                            ]:
                                deleteMessage(self.__listener.bot, meta)
                                break
                        except BaseException:
                            return deleteMessage(self.__listener.bot, meta)
                self.client.torrents_pause(torrent_hashes=self.ext_hash)
                pincode = ""
                for n in str(self.ext_hash):
                    if n.isdigit():
                        pincode += str(n)
                    if len(pincode) == 4:
                        break
                buttons = button_build.ButtonMaker()
                gid = self.ext_hash[:12]
                if WEB_PINCODE:
                    buttons.buildbutton(
                        "Select Files", f"{BASE_URL}/app/files/{self.ext_hash}"
                    )
                    buttons.sbutton("Pincode", f"qbs pin {gid} {pincode}")
                else:
                    buttons.buildbutton(
                        "Select Files",
                        f"{BASE_URL}/app/files/{self.ext_hash}?pin_code={pincode}",
                    )
                buttons.sbutton("Done Selecting", f"qbs done {gid} {self.ext_hash}")
                QBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
                msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
                sendMarkup(msg, self.__listener.bot, self.__listener.message, QBBUTTONS)
            else:
                sendStatusMessage(self.__listener.message, self.__listener.bot)
        except Exception as e:
            sendMessage(str(e), self.__listener.bot, self.__listener.message)
            self.client.auth_log_out()

    def __qb_listener(self):
        try:
            tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
            if len(tor_info) == 0:
                return
            tor_info = tor_info[0]
            if tor_info.state == "metaDL":
                self.__stalled_time = time()
                if (
                    TORRENT_TIMEOUT is not None
                    and time() - tor_info.added_on >= TORRENT_TIMEOUT
                ):
                    self.__onDownloadError("★ 𝗠𝗔𝗚𝗡𝗘𝗧/𝗧𝗢𝗥𝗥𝗘𝗡𝗧 𝗟𝗜𝗡𝗞 𝗜𝗦 𝗗𝗘𝗔𝗗 ❌ ★")
            elif tor_info.state == "downloading":
                self.__stalled_time = time()
                if (
                    not self.__dupChecked
                    and STOP_DUPLICATE
                    and ospath.isdir(f"{self.__path}")
                    and not self.__listener.isLeech
                ):
                    LOGGER.info("Checking File/Folder if already in Drive")
                    qbname = str(listdir(f"{self.__path}")[-1])
                    if qbname.endswith(".!qB"):
                        qbname = ospath.splitext(qbname)[0]
                    if self.__listener.isZip:
                        qbname = qbname + ".zip"
                    elif self.__listener.extract:
                        try:
                            qbname = get_base_name(qbname)
                        except Exception:
                            qbname = None
                    if qbname is not None:
                        qbmsg, button = GoogleDriveHelper().drive_list(qbname, True)
                        if qbmsg:
                            self.__onDownloadError(
                                "𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗶𝗻 𝗗𝗿𝗶𝘃𝗲."
                            )
                            sendMarkup(
                                "𝗛𝗲𝗿𝗲 𝗮𝗿𝗲 𝘁𝗵𝗲 𝘀𝗲𝗮𝗿𝗰𝗵 𝗿𝗲𝘀𝘂𝗹𝘁𝘀: ",
                                self.__listener.bot,
                                self.__listener.message,
                                button,
                            )
                    self.__dupChecked = True
                if not self.__sizeChecked:
                    size = tor_info.size
                    arch = any([self.__listener.isZip, self.__listener.extract])
                    if STORAGE_THRESHOLD is not None:
                        acpt = check_storage_threshold(size, arch)
                        if not acpt:
                            msg = f"𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗹𝗲𝗮𝘃𝗲 {STORAGE_THRESHOLD}𝗚𝗕 𝗳𝗿𝗲𝗲 𝘀𝘁𝗼𝗿𝗮𝗴𝗲."
                            msg += f"\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}"
                            self.__onDownloadError(msg)
                            return
                    limit = None
                    if ZIP_UNZIP_LIMIT is not None and arch:
                        mssg = f"𝗭𝗶𝗽/𝗨𝗻𝘇𝗶𝗽 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {ZIP_UNZIP_LIMIT}𝗚𝗕"
                        limit = ZIP_UNZIP_LIMIT
                    elif TORRENT_DIRECT_LIMIT is not None:
                        mssg = f"𝗧𝗼𝗿𝗿𝗲𝗻𝘁/𝗗𝗶𝗿𝗲𝗰𝘁 𝗹𝗶𝗺𝗶𝘁 𝗶𝘀 {TORRENT_DIRECT_LIMIT}𝗚𝗕"
                        limit = TORRENT_DIRECT_LIMIT
                    if limit is not None:
                        LOGGER.info("Checking File/Folder Size...")
                        if size > limit * 1024**3:
                            fmsg = f"{mssg}.\n𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲/𝗙𝗼𝗹𝗱𝗲𝗿 𝘀𝗶𝘇𝗲 𝗶𝘀 {get_readable_file_size(size)}"
                            self.__onDownloadError(fmsg)
                    self.__sizeChecked = True
            elif tor_info.state == "stalledDL":
                if not self.__rechecked and 0.99989999999999999 < tor_info.progress < 1:
                    msg = f"Force recheck - Name: {self.__name} Hash: "
                    msg += f"{self.ext_hash} Downloaded Bytes: {tor_info.downloaded} "
                    msg += f"Size: {tor_info.size} Total Size: {tor_info.total_size}"
                    LOGGER.info(msg)
                    self.client.torrents_recheck(torrent_hashes=self.ext_hash)
                    self.__rechecked = True
                elif (
                    TORRENT_TIMEOUT is not None
                    and time() - self.__stalled_time >= TORRENT_TIMEOUT
                ):
                    self.__onDownloadError("★ 𝗠𝗔𝗚𝗡𝗘𝗧/𝗧𝗢𝗥𝗥𝗘𝗡𝗧 𝗟𝗜𝗡𝗞 𝗜𝗦 𝗗𝗘𝗔𝗗 ❌ ★")
            elif tor_info.state == "missingFiles":
                self.client.torrents_recheck(torrent_hashes=self.ext_hash)
            elif tor_info.state == "error":
                self.__onDownloadError("𝗡𝗼𝘁 𝗲𝗻𝗼𝘂𝗴𝗵 𝘀𝗽𝗮𝗰𝗲 𝗳𝗼𝗿 𝘁𝗵𝗶𝘀 𝘁𝗼𝗿𝗿𝗲𝗻𝘁 𝗼𝗻 𝗱𝗲𝘃𝗶𝗰𝗲")
            elif (
                (tor_info.state.lower().endswith("up") or tor_info.state == "uploading")
                and not self.__uploaded
                and len(listdir(self.__path)) != 0
            ):
                self.__uploaded = True
                if not QB_SEED:
                    self.client.torrents_pause(torrent_hashes=self.ext_hash)
                if self.select:
                    clean_unwanted(self.__path)
                self.__listener.onDownloadComplete()
                if (
                    QB_SEED
                    and not self.__listener.isLeech
                    and not self.__listener.extract
                ):
                    with download_dict_lock:
                        if self.__listener.uid not in list(download_dict.keys()):
                            self.client.torrents_delete(
                                torrent_hashes=self.ext_hash, delete_files=True
                            )
                            self.client.auth_log_out()
                            self.periodic.cancel()
                            return
                        download_dict[self.__listener.uid] = QbDownloadStatus(
                            self.__listener, self
                        )
                    self.__seeding = True
                    update_all_messages()
                    LOGGER.info(f"Seeding started: {self.__name}")
                else:
                    self.client.torrents_delete(
                        torrent_hashes=self.ext_hash, delete_files=True
                    )
                    self.client.auth_log_out()
                    self.periodic.cancel()
            elif tor_info.state == "pausedUP" and QB_SEED:
                self.__listener.onUploadError(
                    f"Seeding stopped with Ratio: {round(tor_info.ratio, 3)} and Time: {get_readable_time(tor_info.seeding_time)}"
                )
                self.client.torrents_delete(
                    torrent_hashes=self.ext_hash, delete_files=True
                )
                self.client.auth_log_out()
                self.periodic.cancel()
        except Exception as e:
            LOGGER.error(str(e))

    def __onDownloadError(self, err):
        LOGGER.info(f"Cancelling Download: {self.__name}")
        self.client.torrents_pause(torrent_hashes=self.ext_hash)
        sleep(0.3)
        self.__listener.onDownloadError(err)
        self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
        self.client.auth_log_out()
        self.periodic.cancel()

    def cancel_download(self):
        if self.__seeding:
            LOGGER.info(f"Cancelling Seed: {self.__name}")
            self.client.torrents_pause(torrent_hashes=self.ext_hash)
        else:
            self.__onDownloadError("Download stopped by user!")


def get_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(" ")
    qbdl = getDownloadByGid(data[2])
    if not qbdl:
        query.answer(text="This task has been cancelled!", show_alert=True)
        query.message.delete()
    elif user_id != qbdl.listener().message.from_user.id:
        query.answer(text="This task is not for you!", show_alert=True)
    elif data[1] == "pin":
        query.answer(text=data[3], show_alert=True)
    elif data[1] == "done":
        query.answer()
        qbdl.client().torrents_resume(torrent_hashes=data[3])
        sendStatusMessage(qbdl.listener().message, qbdl.listener().bot)
        query.message.delete()


"""
def _get_hash_magnet(mgt: str):
    if 'xt=urn:btmh:' in mgt:
        hash_ = re_search(r'(?<=xt=urn:btmh:)[a-zA-Z0-9]+', mgt).group(0)
    else:
        hash_ = re_search(r'(?<=xt=urn:btih:)[a-zA-Z0-9]+', mgt).group(0)
    if len(hash_) == 32:
        hash_ = b16encode(b32decode(str(hash_))).decode()
    return str(hash_)

def _get_hash_file(path, v2=False):
    with open(path, "rb") as f:
        decodedDict = bdecode(f.read())
    if v2:
        hash_ = sha256(bencode(decodedDict[b'info'])).hexdigest()
    else:
        hash_ = sha1(bencode(decodedDict[b'info'])).hexdigest()
    if len(hash_) == 64:
        hash_ = hash_[:40]
    return str(hash_)
"""

qbs_handler = CallbackQueryHandler(get_confirm, pattern="qbs", run_async=True)
dispatcher.add_handler(qbs_handler)
