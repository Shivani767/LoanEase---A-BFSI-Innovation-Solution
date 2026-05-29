from __future__ import annotations

import logging
import re

logger = logging.getLogger("loanease.aadhaar")


def extract_mobile_from_aadhaar(text: str) -> str | None:
    """Extract a registered mobile number from full Aadhaar OCR text."""
    clean = re.sub(r"\s+", " ", text or "")
    compact = re.sub(r"\s+", "", clean)

    patterns = [
        r"(?:Mobile|Mob|Ph|Phone|Contact)[:\s.]*([6-9]\d{9})",
        r"\b([6-9]\d{9})\b",
        r"(?:\+91|91)[\s-]?([6-9]\d{9})",
        r"\b([6-9]\d{2})\s(\d{4})\s(\d{3})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean, re.IGNORECASE)
        if not match:
            match = re.search(pattern, compact, re.IGNORECASE)
        if not match:
            continue

        if len(match.groups()) == 1:
            number = re.sub(r"\D", "", match.group(1))
        else:
            number = "".join(match.groups())

        if len(number) == 10 and number[0] in "6789":
            logger.info("Mobile extracted from Aadhaar OCR: XXXXXX%s", number[-4:])
            return number

    logger.warning("Mobile not found in Aadhaar OCR")
    return None
