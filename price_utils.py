"""
Shared price extraction utilities.
"""

import re
from typing import Optional

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def normalize_digits(text: str) -> str:
    for i, ch in enumerate(PERSIAN_DIGITS):
        text = text.replace(ch, str(i))
    for i, ch in enumerate(ARABIC_DIGITS):
        text = text.replace(ch, str(i))
    return text


_PRICE_PATTERNS = [
    r"([\d,،۰-۹٠-٩]+(?:[,،][\d۰-۹٠-٩]+)*)\s*(?:تومان|ریال|تومن)",
    r"(?:قیمت|نرخ|قيمت)[:\s]+([۰-۹٠-٩\d][۰-۹٠-٩\d,،.]*)",
    r"\b([\d۰-۹٠-٩]{1,3}(?:[,،][\d۰-۹٠-٩]{3})+)\b",
    r"\b(\d{4,})\b",
]
_COMPILED = [re.compile(p, re.UNICODE) for p in _PRICE_PATTERNS]


def extract_price(text: str) -> Optional[str]:
    normalized = normalize_digits(text)
    for pattern in _COMPILED:
        match = pattern.search(normalized)
        if match:
            raw = match.group(1).replace("،", ",").strip()
            digits_only = raw.replace(",", "")
            if digits_only.isdigit() and len(digits_only) >= 3:
                return raw
    return None
