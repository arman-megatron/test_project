import os

# ---------------------------------------------------------------------------
# Telegram public channels (scraped via t.me/s)
# ---------------------------------------------------------------------------
TELEGRAM_CHANNELS = [
    "bazargahkilooton",
    "ahanprice",
    "atifoolad",
    "civilmashhadd",
    "PipeBazaar",
]

# Private Telegram groups require Telethon + user login — not yet supported.
# IDs for future Telethon integration:
PRIVATE_TELEGRAM_IDS = [
    -1001223600036,
    -1001450756247,
    -1002546386516,
    -1001084894820,
    -1002795368908,
]

# ---------------------------------------------------------------------------
# Web sources (scraped directly via HTTP)
# ---------------------------------------------------------------------------
WEB_SOURCES = [
    {
        "name": "IranJib",
        "url": "https://www.iranjib.ir/showgroup/38/%D9%82%DB%8C%D9%85%D8%AA-%D8%A2%D9%87%D9%86-%D8%A2%D9%84%D8%A7%D8%AA/",
        "type": "iranjib",
    },
    {
        "name": "Ahangar",
        "url": "https://ahangar.com/",
        "type": "generic",
    },
    {
        "name": "AhanMelal",
        "url": "https://ahanmelal.com/",
        "type": "generic",
    },
    {
        "name": "BalabarSakhtamani",
        "url": "https://www.balabarsakhtemani.com/",
        "type": "generic",
    },
    {
        "name": "LoolehOnline",
        "url": "https://loolehonline.com/",
        "type": "generic",
    },
]

# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------
GOOGLE_SHEET_ID = os.environ.get(
    "GOOGLE_SHEET_ID", "1X9ptoKcrK7o0sOvz_NngBxxgfgLehqnEqu0Ouk2PdHE"
)
SHEET_TAB_INDEX = int(os.environ.get("SHEET_TAB_INDEX", "0"))

CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "credentials.json")

SHEET_COLUMNS = ["Date", "Channel", "Price", "Full_Message", "Message_Link", "Extracted_At"]

# ---------------------------------------------------------------------------
# Scraping behaviour
# ---------------------------------------------------------------------------
DELAY_BETWEEN_CHANNELS = float(os.environ.get("DELAY_BETWEEN_CHANNELS", "4.0"))
DELAY_BETWEEN_MESSAGES = float(os.environ.get("DELAY_BETWEEN_MESSAGES", "0.5"))
MAX_MESSAGES_PER_CHANNEL = int(os.environ.get("MAX_MESSAGES_PER_CHANNEL", "20"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Proxy (optional, for use behind VPN/sanctions)
# ---------------------------------------------------------------------------
PROXIES = None
HTTP_PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
HTTPS_PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
if HTTP_PROXY or HTTPS_PROXY:
    PROXIES = {
        "http": HTTP_PROXY,
        "https": HTTPS_PROXY,
    }

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "price_tracker.log")
