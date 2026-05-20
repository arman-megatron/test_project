"""
Telegram Price Tracker
Scrapes public Telegram channels (via t.me/s) + Iranian steel/construction
websites and saves all prices to a Google Sheet.
"""

import re
import time
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

import config
from price_utils import extract_price, normalize_digits
from web_scrapers import scrape_web_source

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("price_tracker")

# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    if config.PROXIES:
        session.proxies.update(config.PROXIES)
        logger.info("Using proxy: %s", config.PROXIES)
    return session


# ---------------------------------------------------------------------------
# Telegram public channel scraper (t.me/s)
# ---------------------------------------------------------------------------

def fetch_channel_page(session: requests.Session, channel: str) -> Optional[str]:
    url = f"https://t.me/s/{channel}"
    try:
        resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.SSLError:
        logger.warning("SSL error for @%s — retrying without verification", channel)
        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT, verify=False)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.error("Failed to fetch @%s (no-verify): %s", channel, exc)
            return None
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to fetch @%s: %s", channel, exc)
        return None


def parse_telegram_messages(html: str, channel: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []

    wrappers = soup.select("div.tgme_widget_message_wrap")
    logger.debug("@%s: found %d message wrappers", channel, len(wrappers))

    for wrapper in wrappers[-config.MAX_MESSAGES_PER_CHANNEL:]:
        text_el = wrapper.select_one("div.tgme_widget_message_text")
        if not text_el:
            continue

        full_text = text_el.get_text(separator="\n").strip()
        if not full_text:
            continue

        price = extract_price(full_text)
        if not price:
            continue

        link_el = wrapper.select_one("a.tgme_widget_message_date")
        message_link = link_el["href"] if link_el and link_el.has_attr("href") else ""

        time_el = wrapper.select_one("time")
        raw_date = (
            time_el["datetime"][:10]
            if time_el and time_el.has_attr("datetime")
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        results.append(
            {
                "Date": raw_date,
                "Channel": f"@{channel}",
                "Price": price,
                "Full_Message": full_text[:1000],
                "Message_Link": message_link,
                "Extracted_At": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),
            }
        )
        time.sleep(config.DELAY_BETWEEN_MESSAGES)

    logger.info("@%s: extracted %d price records", channel, len(results))
    return results


def scrape_telegram_channels(session: requests.Session) -> list[dict]:
    all_records = []
    for channel in config.TELEGRAM_CHANNELS:
        logger.info("--- Telegram @%s ---", channel)
        html = fetch_channel_page(session, channel)
        if html:
            all_records.extend(parse_telegram_messages(html, channel))
        else:
            logger.warning("Skipping @%s (no response)", channel)
        time.sleep(config.DELAY_BETWEEN_CHANNELS)
    return all_records


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_worksheet() -> gspread.Worksheet:
    creds = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    logger.info("Opened Google Sheet ID: %s", config.GOOGLE_SHEET_ID)

    worksheet = sheet.get_worksheet(config.SHEET_TAB_INDEX)
    existing = worksheet.get_all_values()
    if not existing:
        worksheet.append_row(config.SHEET_COLUMNS)
        logger.info("Added header row to sheet")
    elif existing[0] != config.SHEET_COLUMNS:
        # Sheet has content but wrong/missing header — insert header at top
        worksheet.insert_row(config.SHEET_COLUMNS, index=1)
        logger.info("Inserted header row at top of existing sheet")

    return worksheet


def load_existing_links(worksheet: gspread.Worksheet) -> set[str]:
    try:
        link_col_idx = config.SHEET_COLUMNS.index("Message_Link") + 1
        col_values = worksheet.col_values(link_col_idx)
        return set(v for v in col_values[1:] if v)
    except Exception as exc:
        logger.warning("Could not load existing links: %s", exc)
        return set()


def deduplicate(records: list[dict], seen_links: set[str]) -> list[dict]:
    fresh = []
    for r in records:
        link = r.get("Message_Link", "").strip()
        key = link if link else r.get("Full_Message", "")[:120]
        if key and key in seen_links:
            continue
        fresh.append(r)
        seen_links.add(key)
    return fresh


def append_rows(worksheet: gspread.Worksheet, records: list[dict]) -> int:
    if not records:
        return 0
    rows = [[r.get(col, "") for col in config.SHEET_COLUMNS] for r in records]
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    logger.info("=== Telegram Price Tracker started ===")
    session = build_session()

    logger.info("Connecting to Google Sheets (ID: %s)…", config.GOOGLE_SHEET_ID)
    try:
        worksheet = get_worksheet()
    except Exception as exc:
        logger.critical("Cannot connect to Google Sheets: %s", exc)
        sys.exit(1)

    seen_links = load_existing_links(worksheet)
    logger.info("Loaded %d existing entries for deduplication", len(seen_links))

    all_records: list[dict] = []

    # --- Telegram channels ---
    logger.info("== Scraping Telegram channels ==")
    all_records.extend(scrape_telegram_channels(session))

    # --- Web sources ---
    logger.info("== Scraping web sources ==")
    for source in config.WEB_SOURCES:
        logger.info("--- Web: %s ---", source["name"])
        records = scrape_web_source(session, source)
        all_records.extend(records)
        time.sleep(config.DELAY_BETWEEN_CHANNELS)

    # --- Deduplicate & write ---
    fresh = deduplicate(all_records, seen_links)
    logger.info("Total raw records: %d | New (after dedup): %d", len(all_records), len(fresh))

    if fresh:
        written = append_rows(worksheet, fresh)
        logger.info("Wrote %d rows to Google Sheet", written)
    else:
        logger.info("No new records to write.")

    logger.info("=== Done ===")


if __name__ == "__main__":
    run()
