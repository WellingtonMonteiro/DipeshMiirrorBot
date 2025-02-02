from faulthandler import enable as faulthandler_enable
from json import loads as jsnloads
from logging import INFO, FileHandler, StreamHandler, basicConfig
from logging import error as log_error
from logging import getLogger
from logging import info as log_info
from logging import warning as log_warning
from os import environ
from os import path as ospath
from os import remove as osremove
from socket import setdefaulttimeout
from subprocess import Popen, check_output
from subprocess import run as srun
from threading import Lock, Thread
from time import sleep, time

from aria2p import API as ariaAPI
from aria2p import Client as ariaClient
from dotenv import load_dotenv
from megasdkrestclient import errors as mega_err
from pyrogram import Client, enums
from qbittorrentapi import Client as qbClient
from requests import get as rget
from telegram.ext import Updater as tgUpdater

EXTENTION_FILTER = set([".!qB", ".parts", ".torrent"])

faulthandler_enable()

setdefaulttimeout(600)

botStartTime = time()

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

LOGGER = getLogger(__name__)

load_dotenv("config.env", override=True)


def getConfig(name: str):
    return environ[name]


try:
    NETRC_URL = getConfig("NETRC_URL")
    if len(NETRC_URL) == 0:
        raise KeyError
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open(".netrc", "wb+") as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")
except Exception:
    pass
try:
    SERVER_PORT = getConfig("SERVER_PORT")
    if len(SERVER_PORT) == 0:
        raise KeyError
except Exception:
    SERVER_PORT = 80

PORT = environ.get("PORT", SERVER_PORT)
alive = Popen(["python3", "alive.py"])
Popen([f"gunicorn web.wserver:app --bind 0.0.0.0:{PORT}"], shell=True)
srun(["qbittorrent-nox", "-d", "--profile=."])
if not ospath.exists(".netrc"):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])
srun(["chmod", "+x", "aria.sh"])
srun(["./aria.sh"], shell=True)

Interval = []
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []

try:
    if bool(getConfig("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit()
except Exception:
    pass

aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret="",
    )
)


def get_client():
    return qbClient(host="localhost", port=8090)


trackers = check_output(
    [
        "curl -Ns https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt https://ngosang.github.io/trackerslist/trackers_all_http.txt https://newtrackon.com/api/all | awk '$0'"
    ],
    shell=True,
).decode("utf-8")
trackerslist = set(trackers.split("\n"))
trackerslist.remove("")
trackerslist = "\n\n".join(trackerslist)
get_client().application.set_preferences({"add_trackers": f"{trackerslist}"})

DOWNLOAD_DIR = None
BOT_TOKEN = None

try:
    BOT_TOKEN = getConfig("BOT_TOKEN")
    parent_id = getConfig("GDRIVE_FOLDER_ID")
    DOWNLOAD_DIR = getConfig("DOWNLOAD_DIR")
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = f"{DOWNLOAD_DIR}/"
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig("DOWNLOAD_STATUS_UPDATE_INTERVAL"))
    OWNER_ID = int(getConfig("OWNER_ID"))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig("AUTO_DELETE_MESSAGE_DURATION"))
    TELEGRAM_API = getConfig("TELEGRAM_API")
    TELEGRAM_HASH = getConfig("TELEGRAM_HASH")
except KeyError:
    LOGGER.error("One or more env variables missing! Exiting now")
    exit(1)

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# key: rss_title
# value: [rss_feed, last_link, last_title, filter]
rss_dict = {}

AUTHORIZED_CHATS = set()
SUDO_USERS = set()
AS_DOC_USERS = set()
AS_MEDIA_USERS = set()
MIRROR_LOGS = set()
LINK_LOGS = set()
LEECH_LOG = set()
LEECH_LOG_ALT = set()
EXTENTION_FILTER = set([".torrent"])

if ospath.exists("authorized_chats.txt"):
    with open("authorized_chats.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            AUTHORIZED_CHATS.add(int(line.split()[0]))
if ospath.exists("sudo_users.txt"):
    with open("sudo_users.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            SUDO_USERS.add(int(line.split()[0]))
if ospath.exists("link_logs.txt"):
    with open("link_logs.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            #    LOGGER.info(line.split())
            LINK_LOGS.add(int(line.split()[0]))
if ospath.exists("logs_chat.txt"):
    with open("logs_chat.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            #    LOGGER.info(line.split())
            MIRROR_LOGS.add(int(line.split()[0]))

if ospath.exists("leech.txt"):
    with open("leech.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            #    LOGGER.info(line.split())
            LEECH_LOG.add(int(line.split()[0]))

if ospath.exists("leech_logs.txt"):
    with open("leech_logs.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            #    LOGGER.info(line.split())
            LEECH_LOG_ALT.add(int(line.split()[0]))

try:
    achats = getConfig("AUTHORIZED_CHATS")
    achats = achats.split(" ")
    for chats in achats:
        AUTHORIZED_CHATS.add(int(chats))
except Exception:
    pass

try:
    schats = getConfig("SUDO_USERS")
    schats = schats.split(" ")
    for chats in schats:
        SUDO_USERS.add(int(chats))
except Exception:
    pass

try:
    achats = getConfig("MIRROR_LOGS")
    achats = achats.split(" ")
    for chats in achats:
        MIRROR_LOGS.add(int(chats))
except Exception:
    log_warning("Logs Chat Details not provided!")

try:
    achats = getConfig("LINK_LOGS")
    achats = achats.split(" ")
    for chats in achats:
        LINK_LOGS.add(int(chats))
except Exception:
    log_warning("LINK_LOGS Chat id not provided, Proceeding Without it")

try:
    achats = getConfig("LEECH_LOG")
    achats = achats.split(" ")
    for chats in achats:
        LEECH_LOG.add(int(chats))
except Exception:
    log_warning("Leech Log Channel ID not Provided!")

try:
    achats = getConfig("LEECH_LOG_ALT")
    achats = achats.split(" ")
    for chats in achats:
        LEECH_LOG_ALT.add(int(chats))
except Exception:
    log_warning("Leech Log alt Channel ID not Provided!")

try:
    fx = getConfig("EXTENTION_FILTER")
    if len(fx) > 0:
        fx = fx.split(" ")
        for x in fx:
            EXTENTION_FILTER.add(x.lower())
except Exception:
    pass

LOGGER.info("Generating BOT_STRING_SESSION")
app = Client(
    name="pyrogram",
    api_id=int(TELEGRAM_API),
    api_hash=TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML,
    no_updates=True,
)

try:
    USER_STRING_SESSION = getConfig("USER_STRING_SESSION")
    if len(USER_STRING_SESSION) == 0:
        raise KeyError
    rss_session = Client(
        name="rss_session",
        api_id=int(TELEGRAM_API),
        api_hash=TELEGRAM_HASH,
        session_string=USER_STRING_SESSION,
        parse_mode=enums.ParseMode.HTML,
    )
except Exception:
    USER_STRING_SESSION = None
    rss_session = None


def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = (
            "https://releases.ubuntu.com/21.10/ubuntu-21.10-desktop-amd64.iso.torrent"
        )
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {"dir": dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(20)
        for download in downloads:
            aria2.remove([download], force=True, files=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")


Thread(target=aria2c_init).start()
sleep(1.5)

try:
    DB_URI = getConfig("DATABASE_URL")
    if len(DB_URI) == 0:
        raise KeyError
except BaseException:
    DB_URI = None
try:
    TG_SPLIT_SIZE = getConfig("TG_SPLIT_SIZE")
    if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > 2097151000:
        raise KeyError
    TG_SPLIT_SIZE = int(TG_SPLIT_SIZE)
except BaseException:
    TG_SPLIT_SIZE = 2097151000
try:
    STATUS_LIMIT = getConfig("STATUS_LIMIT")
    if len(STATUS_LIMIT) == 0:
        raise KeyError
    STATUS_LIMIT = int(STATUS_LIMIT)
except BaseException:
    STATUS_LIMIT = None
try:
    MEGA_KEY = getConfig("MEGA_API_KEY")
    if len(MEGA_KEY) == 0:
        raise KeyError
except BaseException:
    MEGA_KEY = None
    LOGGER.info("MEGA_API_KEY not provided!")
if MEGA_KEY is not None:
    # Start megasdkrest binary
    Popen(["megasdkrest", "--apikey", MEGA_KEY])
    sleep(3)  # Wait for the mega server to start listening
    mega_client = MegaSdkRestClient("http://localhost:6090")
    try:
        MEGA_USERNAME = getConfig("MEGA_EMAIL_ID")
        MEGA_PASSWORD = getConfig("MEGA_PASSWORD")
        if len(MEGA_USERNAME) > 0 and len(MEGA_PASSWORD) > 0:
            try:
                mega_client.login(MEGA_USERNAME, MEGA_PASSWORD)
            except mega_err.MegaSdkRestClientException as e:
                log_error(e.message["message"])
                exit(0)
        else:
            log_info(
                "Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!"
            )
    except BaseException:
        log_info(
            "Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!"
        )
else:
    sleep(1.5)
try:
    UPTOBOX_TOKEN = getConfig("UPTOBOX_TOKEN")
    if len(UPTOBOX_TOKEN) == 0:
        raise KeyError
except BaseException:
    UPTOBOX_TOKEN = None
try:
    INDEX_URL = getConfig("INDEX_URL").rstrip("/")
    if len(INDEX_URL) == 0:
        raise KeyError
    INDEX_URLS.append(INDEX_URL)
except BaseException:
    INDEX_URL = None
    INDEX_URLS.append(None)
try:
    SEARCH_API_LINK = getConfig("SEARCH_API_LINK").rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        raise KeyError
except BaseException:
    SEARCH_API_LINK = None
try:
    SEARCH_LIMIT = getConfig("SEARCH_LIMIT")
    if len(SEARCH_LIMIT) == 0:
        raise KeyError
    SEARCH_LIMIT = int(SEARCH_LIMIT)
except BaseException:
    SEARCH_LIMIT = 0
try:
    RSS_COMMAND = getConfig("RSS_COMMAND")
    if len(RSS_COMMAND) == 0:
        raise KeyError
except BaseException:
    RSS_COMMAND = None
try:
    CMD_INDEX = getConfig("CMD_INDEX")
    if len(CMD_INDEX) == 0:
        raise KeyError
except BaseException:
    CMD_INDEX = ""
try:
    TORRENT_DIRECT_LIMIT = getConfig("TORRENT_DIRECT_LIMIT")
    if len(TORRENT_DIRECT_LIMIT) == 0:
        raise KeyError
    TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT)
except BaseException:
    TORRENT_DIRECT_LIMIT = None
try:
    CLONE_LIMIT = getConfig("CLONE_LIMIT")
    if len(CLONE_LIMIT) == 0:
        raise KeyError
    CLONE_LIMIT = float(CLONE_LIMIT)
except BaseException:
    CLONE_LIMIT = None
try:
    MEGA_LIMIT = getConfig("MEGA_LIMIT")
    if len(MEGA_LIMIT) == 0:
        raise KeyError
    MEGA_LIMIT = float(MEGA_LIMIT)
except BaseException:
    MEGA_LIMIT = None
try:
    STORAGE_THRESHOLD = getConfig("STORAGE_THRESHOLD")
    if len(STORAGE_THRESHOLD) == 0:
        raise KeyError
    STORAGE_THRESHOLD = float(STORAGE_THRESHOLD)
except BaseException:
    STORAGE_THRESHOLD = None
try:
    ZIP_UNZIP_LIMIT = getConfig("ZIP_UNZIP_LIMIT")
    if len(ZIP_UNZIP_LIMIT) == 0:
        raise KeyError
    ZIP_UNZIP_LIMIT = float(ZIP_UNZIP_LIMIT)
except BaseException:
    ZIP_UNZIP_LIMIT = None
try:
    RSS_CHAT_ID = getConfig("RSS_CHAT_ID")
    if len(RSS_CHAT_ID) == 0:
        raise KeyError
    RSS_CHAT_ID = int(RSS_CHAT_ID)
except BaseException:
    RSS_CHAT_ID = None
try:
    RSS_DELAY = getConfig("RSS_DELAY")
    if len(RSS_DELAY) == 0:
        raise KeyError
    RSS_DELAY = int(RSS_DELAY)
except BaseException:
    RSS_DELAY = 900
try:
    TORRENT_TIMEOUT = getConfig("TORRENT_TIMEOUT")
    if len(TORRENT_TIMEOUT) == 0:
        raise KeyError
    TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
except BaseException:
    TORRENT_TIMEOUT = None
try:
    BUTTON_FOUR_NAME = getConfig("BUTTON_FOUR_NAME")
    BUTTON_FOUR_URL = getConfig("BUTTON_FOUR_URL")
    if len(BUTTON_FOUR_NAME) == 0 or len(BUTTON_FOUR_URL) == 0:
        raise KeyError
except BaseException:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None
try:
    BUTTON_FIVE_NAME = getConfig("BUTTON_FIVE_NAME")
    BUTTON_FIVE_URL = getConfig("BUTTON_FIVE_URL")
    if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
        raise KeyError
except BaseException:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None
try:
    BUTTON_SIX_NAME = getConfig("BUTTON_SIX_NAME")
    BUTTON_SIX_URL = getConfig("BUTTON_SIX_URL")
    if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
        raise KeyError
except BaseException:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None
try:
    INCOMPLETE_TASK_NOTIFIER = getConfig("INCOMPLETE_TASK_NOTIFIER")
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"
except BaseException:
    INCOMPLETE_TASK_NOTIFIER = False
try:
    STOP_DUPLICATE = getConfig("STOP_DUPLICATE")
    STOP_DUPLICATE = STOP_DUPLICATE.lower() == "true"
except BaseException:
    STOP_DUPLICATE = False
try:
    VIEW_LINK = getConfig("VIEW_LINK")
    VIEW_LINK = VIEW_LINK.lower() == "true"
except BaseException:
    VIEW_LINK = False
try:
    IS_TEAM_DRIVE = getConfig("IS_TEAM_DRIVE")
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == "true"
except BaseException:
    IS_TEAM_DRIVE = False
try:
    USE_SERVICE_ACCOUNTS = getConfig("USE_SERVICE_ACCOUNTS")
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == "true"
except BaseException:
    USE_SERVICE_ACCOUNTS = False
try:
    BLOCK_MEGA_FOLDER = getConfig("BLOCK_MEGA_FOLDER")
    BLOCK_MEGA_FOLDER = BLOCK_MEGA_FOLDER.lower() == "true"
except BaseException:
    BLOCK_MEGA_FOLDER = False
try:
    BLOCK_MEGA_LINKS = getConfig("BLOCK_MEGA_LINKS")
    BLOCK_MEGA_LINKS = BLOCK_MEGA_LINKS.lower() == "true"
except BaseException:
    BLOCK_MEGA_LINKS = False
try:
    WEB_PINCODE = getConfig("WEB_PINCODE")
    WEB_PINCODE = WEB_PINCODE.lower() == "true"
except BaseException:
    WEB_PINCODE = False
try:
    SHORTENER = getConfig("SHORTENER")
    SHORTENER_API = getConfig("SHORTENER_API")
    if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
        raise KeyError
except BaseException:
    SHORTENER = None
    SHORTENER_API = None
try:
    IGNORE_PENDING_REQUESTS = getConfig("IGNORE_PENDING_REQUESTS")
    IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == "true"
except BaseException:
    IGNORE_PENDING_REQUESTS = False
try:
    BASE_URL = getConfig("BASE_URL_OF_BOT").rstrip("/")
    if len(BASE_URL) == 0:
        raise KeyError
except BaseException:
    log_warning("BASE_URL_OF_BOT not provided!")
    BASE_URL = None
try:
    AS_DOCUMENT = getConfig("AS_DOCUMENT")
    AS_DOCUMENT = AS_DOCUMENT.lower() == "true"
except BaseException:
    AS_DOCUMENT = False
try:
    IMAGE_LEECH = getConfig("IMAGE_LEECH")
    IMAGE_LEECH = IMAGE_LEECH.lower() == "true"
except KeyError:
    IMAGE_LEECH = False
try:
    EQUAL_SPLITS = getConfig("EQUAL_SPLITS")
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == "true"
except BaseException:
    EQUAL_SPLITS = False
try:
    QB_SEED = getConfig("QB_SEED")
    QB_SEED = QB_SEED.lower() == "true"
except BaseException:
    QB_SEED = False
try:
    CUSTOM_FILENAME = getConfig("CUSTOM_FILENAME")
    if len(CUSTOM_FILENAME) == 0:
        raise KeyError
except KeyError:
    CUSTOM_FILENAME = None
try:
    APPDRIVE_EMAIL = getConfig("APPDRIVE_EMAIL")
    APPDRIVE_PASS = getConfig("APPDRIVE_PASS")
    if len(APPDRIVE_EMAIL) == 0 or len(APPDRIVE_PASS) == 0:
        raise KeyError
except KeyError:
    APPDRIVE_EMAIL = None
    APPDRIVE_PASS = None
try:
    GDTOT_CRYPT = getConfig("GDTOT_CRYPT")
    if len(GDTOT_CRYPT) == 0:
        raise KeyError
except KeyError:
    GDTOT_CRYPT = None
try:
    GD_INFO = getConfig("GD_INFO")
    if len(GD_INFO) == 0:
        raise KeyError
except KeyError:
    GD_INFO = "Uploaded by 👿 Dipesh Mirror Bot"
try:
    TITLE_NAME = getConfig("TITLE_NAME")
    if len(TITLE_NAME) == 0:
        raise KeyError
except KeyError:
    TITLE_NAME = "👿 Dipesh Mirrors Search"
try:
    AUTHOR_NAME = getConfig("AUTHOR_NAME")
    if len(AUTHOR_NAME) == 0:
        raise KeyError
except KeyError:
    AUTHOR_NAME = "👿 Dipesh Mirror Bot"
try:
    AUTHOR_URL = getConfig("AUTHOR_URL")
    if len(AUTHOR_URL) == 0:
        raise KeyError
except KeyError:
    AUTHOR_URL = "https://t.me/toxytech"
try:
    RESTARTED_GROUP_ID = int(getConfig("RESTARTED_GROUP_ID"))
except BaseException:
    RESTARTED_GROUP_ID = None
try:
    TIMEZONE = getConfig("TIMEZONE")
    if len(TIMEZONE) == 0:
        raise KeyError
except KeyError:
    TIMEZONE = "Asia/Kolkata"
try:
    HEROKU_APP_NAME = getConfig("HEROKU_APP_NAME")
    if len(HEROKU_APP_NAME) == 0:
        raise KeyError
except KeyError:
    log_warning("HEROKU_APP_NAME not provided!")
    HEROKU_APP_NAME = None
try:
    HEROKU_API_KEY = getConfig("HEROKU_API_KEY")
    if len(HEROKU_API_KEY) == 0:
        raise KeyError
except KeyError:
    log_warning("HEROKU_API_KEY not provided!")
    HEROKU_API_KEY = None
try:
    LEECH_ENABLED = getConfig("LEECH_ENABLED")
    LEECH_ENABLED = LEECH_ENABLED.lower() == "true"
except BaseException:
    LEECH_ENABLED = False
try:
    BOT_PM = getConfig("BOT_PM")
    if BOT_PM.lower() == "true":
        BOT_PM = "true"
except BaseException:
    log_warning("BOT_PM is disabled")
    BOT_PM = False
try:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(
        getConfig("AUTO_DELETE_UPLOAD_MESSAGE_DURATION")
    )
    if AUTO_DELETE_UPLOAD_MESSAGE_DURATION < 0:
        raise KeyError
except KeyError:
    log_warning(
        "AUTO_DELETE_UPLOAD_MESSAGE_DURATION not provided or is less than 0. Using default value of 10 min (600s)"
    )
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = 600
try:
    FSUB = getConfig("FSUB")
    if FSUB.lower() == "true":
        FSUB = "true"
except BaseException:
    FSUB = False
    LOGGER.info("Force Subscribe is disabled")
try:
    CHANNEL_USERNAME = getConfig("CHANNEL_USERNAME")
    if len(CHANNEL_USERNAME) == 0:
        raise KeyError
except KeyError:
    log_warning("CHANNEL_USERNAME not provided! Using default @DipeshMirror")
    CHANNEL_USERNAME = "@DipeshMirror"
try:
    FSUB_CHANNEL_ID = int(getConfig("FSUB_CHANNEL_ID"))
except KeyError:
    log_warning("CHANNEL_USERNAME not provided! Using default id of @DipeshMirror")
    FSUB_CHANNEL_ID = "-1001577416484"
try:
    TOKEN_PICKLE_URL = getConfig("TOKEN_PICKLE_URL")
    if len(TOKEN_PICKLE_URL) == 0:
        raise KeyError
    try:
        res = rget(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open("token.pickle", "wb+") as f:
                f.write(res.content)
        else:
            log_error(
                f"Failed to download token.pickle, link got HTTP response: {res.status_code}"
            )
    except Exception as e:
        log_error(f"TOKEN_PICKLE_URL: {e}")
except BaseException:
    pass
try:
    ACCOUNTS_ZIP_URL = getConfig("ACCOUNTS_ZIP_URL")
    if len(ACCOUNTS_ZIP_URL) == 0:
        raise KeyError
    try:
        res = rget(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open("accounts.zip", "wb+") as f:
                f.write(res.content)
        else:
            log_error(
                f"Failed to download accounts.zip, link got HTTP response: {res.status_code}"
            )
    except Exception as e:
        log_error(f"ACCOUNTS_ZIP_URL: {e}")
        raise KeyError
    srun(["unzip", "-q", "-o", "accounts.zip"])
    srun(["chmod", "-R", "777", "accounts"])
    osremove("accounts.zip")
except BaseException:
    pass
try:
    MULTI_SEARCH_URL = getConfig("MULTI_SEARCH_URL")
    if len(MULTI_SEARCH_URL) == 0:
        raise KeyError
    try:
        res = rget(MULTI_SEARCH_URL)
        if res.status_code == 200:
            with open("drive_folder", "wb+") as f:
                f.write(res.content)
        else:
            log_error(
                f"Failed to download drive_folder, link got HTTP response: {res.status_code}"
            )
    except Exception as e:
        log_error(f"MULTI_SEARCH_URL: {e}")
except BaseException:
    pass
try:
    YT_COOKIES_URL = getConfig("YT_COOKIES_URL")
    if len(YT_COOKIES_URL) == 0:
        raise KeyError
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open("cookies.txt", "wb+") as f:
                f.write(res.content)
        else:
            log_error(
                f"Failed to download cookies.txt, link got HTTP response: {res.status_code}"
            )
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")
except BaseException:
    pass

DRIVES_NAMES.append("Main")
DRIVES_IDS.append(parent_id)
if ospath.exists("drive_folder"):
    with open("drive_folder", "r+") as f:
        lines = f.readlines()
        for line in lines:
            try:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace("_", " "))
            except BaseException:
                pass
            try:
                INDEX_URLS.append(temp[2])
            except BaseException:
                INDEX_URLS.append(None)
try:
    SEARCH_PLUGINS = getConfig("SEARCH_PLUGINS")
    if len(SEARCH_PLUGINS) == 0:
        raise KeyError
    SEARCH_PLUGINS = jsnloads(SEARCH_PLUGINS)
except BaseException:
    SEARCH_PLUGINS = None
updater = tgUpdater(
    token=BOT_TOKEN, request_kwargs={"read_timeout": 20, "connect_timeout": 15}
)
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
