"""
Web scrapers for non-Telegram price sources.
Each scraper returns a list of record dicts matching SHEET_COLUMNS.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config
from price_utils import extract_price, normalize_digits

logger = logging.getLogger("price_tracker.web")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


def _fetch(session: requests.Session, url: str) -> Optional[str]:
    try:
        resp = session.get(url, timeout=config.REQUEST_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.exceptions.SSLError:
        try:
            resp = session.get(
                url, timeout=config.REQUEST_TIMEOUT, headers=HEADERS, verify=False
            )
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception as exc:
            logger.error("SSL retry failed for %s: %s", url, exc)
            return None
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# IranJib scraper — iranjib.ir price tables
# ---------------------------------------------------------------------------

def scrape_iranjib(session: requests.Session, source: dict) -> list[dict]:
    url = source["url"]
    html = _fetch(session, url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    records = []

    # IranJib uses product listing cards / table rows
    # Try table rows first
    rows = soup.select("table tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        full_text = " | ".join(c.get_text(strip=True) for c in cells)
        price = extract_price(full_text)
        if not price:
            continue
        link_el = row.find("a", href=True)
        link = link_el["href"] if link_el else url
        if link.startswith("/"):
            link = "https://www.iranjib.ir" + link
        records.append(
            {
                "Date": _now_date(),
                "Channel": source["name"],
                "Price": price,
                "Full_Message": full_text[:1000],
                "Message_Link": link,
                "Extracted_At": _now_ts(),
            }
        )

    # Fallback: product cards
    if not records:
        cards = soup.select(".product-item, .item, .price-box, [class*='product']")
        for card in cards:
            text = card.get_text(separator=" ", strip=True)
            price = extract_price(text)
            if not price:
                continue
            link_el = card.find("a", href=True)
            link = link_el["href"] if link_el else url
            if link.startswith("/"):
                link = "https://www.iranjib.ir" + link
            records.append(
                {
                    "Date": _now_date(),
                    "Channel": source["name"],
                    "Price": price,
                    "Full_Message": text[:1000],
                    "Message_Link": link,
                    "Extracted_At": _now_ts(),
                }
            )

    logger.info("%s: found %d price records", source["name"], len(records))
    return records


# ---------------------------------------------------------------------------
# Generic scraper — tries several common patterns
# ---------------------------------------------------------------------------

_PRICE_SELECTORS = [
    # Common price CSS classes / attributes
    "[class*='price']",
    "[class*='قیمت']",
    "[class*='cost']",
    "[class*='rate']",
    "table tr",
    ".product-item",
    ".item",
    "li",
    "p",
]


def scrape_generic(session: requests.Session, source: dict) -> list[dict]:
    url = source["url"]
    html = _fetch(session, url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    records = []
    seen_texts: set[str] = set()

    base_domain = url.rstrip("/")

    for selector in _PRICE_SELECTORS:
        elements = soup.select(selector)
        for el in elements:
            text = el.get_text(separator=" ", strip=True)
            if not text or text in seen_texts or len(text) < 5:
                continue
            price = extract_price(text)
            if not price:
                continue
            seen_texts.add(text)
            link_el = el.find("a", href=True) or (el if el.name == "a" else None)
            link = ""
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                link = href if href.startswith("http") else base_domain + href

            records.append(
                {
                    "Date": _now_date(),
                    "Channel": source["name"],
                    "Price": price,
                    "Full_Message": text[:1000],
                    "Message_Link": link or url,
                    "Extracted_At": _now_ts(),
                }
            )
            if len(records) >= 30:
                break
        if len(records) >= 30:
            break

    logger.info("%s: found %d price records", source["name"], len(records))
    return records


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

SCRAPER_MAP = {
    "iranjib": scrape_iranjib,
    "generic": scrape_generic,
}


def scrape_web_source(session: requests.Session, source: dict) -> list[dict]:
    scraper_fn = SCRAPER_MAP.get(source.get("type", "generic"), scrape_generic)
    try:
        return scraper_fn(session, source)
    except Exception as exc:
        logger.error("Unhandled error scraping %s: %s", source["name"], exc)
        return []
