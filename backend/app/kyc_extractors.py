from __future__ import annotations

import re
from datetime import datetime, timezone

from rapidfuzz import fuzz

from services.aadhaar_utils import extract_mobile_from_aadhaar


PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
VID_PATTERN = re.compile(r"\b\d{16}\b")
PINCODE_PATTERN = re.compile(r"\b\d{6}\b")

PAN_KEYWORDS = ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "INCOME TAX"]
AADHAAR_KEYWORDS = ["UNIQUE IDENTIFICATION AUTHORITY", "UIDAI", "AADHAAR", "आधार"]

PAN_NON_NAME_HINTS = {
    "INCOME", "TAX", "DEPARTMENT", "PERMANENT", "ACCOUNT", "NUMBER", "GOVT", "GOVERNMENT", "INDIA", "SIGNATURE", "FATHER", "DOB",
}

AADHAAR_NON_NAME_HINTS = {
    "GOVERNMENT", "INDIA", "UNIQUE", "IDENTIFICATION", "AUTHORITY", "UIDAI", "AADHAAR", "ADDRESS", "DOB", "YEAR", "BIRTH", "MALE", "FEMALE", "TRANSGENDER",
}

OCR_DIGIT_MAP = str.maketrans({
    "O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8",
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4", "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
})

AADHAAR_REQUIRED_FIELDS = {
    "aadhaar_last4": "Aadhaar number",
    "name": "Name",
    "date_of_birth": "Date of birth",
    "mobile_number": "Mobile number",
}


def _normalize_pan_candidate(candidate: str) -> str:
    token = re.sub(r"[^A-Z0-9]", "", candidate.upper())
    if len(token) != 10:
        return token
    chars = list(token)
    letter_map = {"0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B"}
    digit_map = {"I": "1", "L": "1", "O": "0", "Q": "0", "D": "0", "S": "5", "B": "8", "Z": "2"}
    for i in [0, 1, 2, 3, 4, 9]:
        chars[i] = letter_map.get(chars[i], chars[i])
    for i in [5, 6, 7, 8]:
        chars[i] = digit_map.get(chars[i], chars[i])
    return "".join(chars)


def _validate_pan_format(pan: str | None) -> bool:
    if not pan or not PAN_PATTERN.fullmatch(pan):
        return False
    pan = pan.upper()
    if pan[3] not in {"P", "C", "H", "F"}:
        return False
    return True


def _extract_pan_number(raw_text: str) -> str | None:
    upper = raw_text.upper()
    direct_match = PAN_PATTERN.search(upper)
    if direct_match:
        return direct_match.group(0)
    
    compact_sources = [upper]
    compact_sources.extend(line.upper() for line in raw_text.splitlines() if line.strip())
    
    for source in compact_sources:
        compact = re.sub(r"[^A-Z0-9]", "", source)
        if len(compact) < 10:
            continue
        
        for start in range(0, len(compact) - 9):
            window = compact[start : start + 10]
            normalized = _normalize_pan_candidate(window)
            if _validate_pan_format(normalized):
                return normalized
        
        # Spaced PAN patterns (e.g., "ABCDE 1234 F")
        spaced_match = re.search(r'([A-Z]{5})\s?([0-9]{4})\s?([A-Z])', source)
        if spaced_match:
            candidate = spaced_match.group(1) + spaced_match.group(2) + spaced_match.group(3)
            if _validate_pan_format(candidate):
                return candidate
    
    return None


def _extract_dob(raw_text: str) -> str | None:
    # Work on a copy with OCR digit corrections only for DOB search
    normalized = raw_text.upper()

    # Explicit date patterns — ordered from most to least specific
    # Do NOT use a bare 8-digit catch-all; it matches Aadhaar numbers
    patterns = [
        # DD/MM/YYYY or D/M/YYYY
        r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b",
        # DD-MM-YYYY
        r"\b(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{4})\b",
        # DD Month YYYY  (e.g. "15 JAN 2003")
        r"\b(\d{1,2})\s+([A-Z]{3,9})\s+(\d{4})\b",
        # DOB: DD/MM/YYYY  (label prefix)
        r"DOB\s*[:\-]?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})",
        # Year of Birth: YYYY  (Aadhaar sometimes only shows year)
        r"(?:YEAR\s+OF\s+BIRTH|YOB)\s*[:\-]?\s*(\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue

        groups = match.groups()

        # Year-only pattern
        if len(groups) == 1:
            year = int(groups[0])
            if 1940 <= year <= 2010:
                # Approximate: use Jan 1 of that year
                return f"01/01/{year}"
            continue

        # Three-group patterns
        if len(groups) == 3:
            g1, g2, g3 = groups

            # Month-name pattern: DD MonthName YYYY
            if g2.isalpha():
                value = f"{g1.zfill(2)} {g2} {g3}"
                for fmt in ["%d %b %Y", "%d %B %Y"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        if 1940 <= dt.year <= 2010:
                            return dt.strftime("%d/%m/%Y")
                    except ValueError:
                        continue
                continue

            # Numeric DD/MM/YYYY or DD-MM-YYYY
            try:
                day, month, year = int(g1), int(g2), int(g3)
            except ValueError:
                continue

            # Sanity check — reject if it looks like an Aadhaar fragment
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1940 <= year <= 2010):
                continue

            try:
                dt = datetime.strptime(f"{day:02d}/{month:02d}/{year}", "%d/%m/%Y")
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue

    return None


def _calculate_age(dob_ddmmyyyy: str | None = None) -> int | None:
    now = datetime.now(timezone.utc)
    if not dob_ddmmyyyy:
        return None
    # Handle year-only approximation (01/01/YYYY)
    try:
        dob = datetime.strptime(dob_ddmmyyyy, "%d/%m/%Y")
        age = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
        return age
    except ValueError:
        return None


def extract_pan(raw_text: str) -> dict:
    text_upper = raw_text.upper()
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    pan_number = _extract_pan_number(raw_text)
    pan_ok = bool(pan_number)
    
    # Extract name
    name = None
    for line in lines:
        if any(hint in line.upper() for hint in ["NAME"]):
            idx = lines.index(line)
            if idx + 1 < len(lines):
                name = lines[idx + 1]
                break
    
    name = (re.sub(r"[^A-Za-z\s]", " ", name or "").strip().upper() if name else None)
    
    dob = _extract_dob(raw_text)
    age = _calculate_age(dob_ddmmyyyy=dob)
    # If age can't be determined from OCR, don't block — assume eligible
    age_ok = (age is None) or (18 <= age <= 70)
    doc_ok = any(keyword in text_upper for keyword in PAN_KEYWORDS)
    
    return {
        "document_type": "PAN",
        "extracted_fields": {
            "pan_number": pan_number,
            "name": name,
            "date_of_birth": dob,
            "age": age,
            "age_eligible": age_ok,
        },
        "validation": {
            "pan_format_valid": pan_ok,
            "name_found": bool(name),
            "dob_found": bool(dob),
            "overall_valid": pan_ok and bool(name) and bool(dob) and age_ok,
        },
    }


def _extract_name_from_aadhaar(raw_text: str) -> str | None:
    """Extract name from Aadhaar card OCR text."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    text_upper = raw_text.upper()

    # Strategy 1: line immediately after "Government of India" / UIDAI header
    skip_patterns = {
        "GOVERNMENT OF INDIA", "GOVT OF INDIA", "UNIQUE IDENTIFICATION",
        "UIDAI", "AADHAAR", "आधार", "भारत सरकार",
    }
    for i, line in enumerate(lines):
        if any(p in line.upper() for p in skip_patterns):
            # Next non-empty line that looks like a name
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                candidate_clean = re.sub(r"[^A-Za-z\s]", "", candidate).strip()
                if (
                    len(candidate_clean) >= 3
                    and candidate_clean.replace(" ", "").isalpha()
                    and not any(p in candidate.upper() for p in skip_patterns)
                    and not any(w in candidate.upper() for w in AADHAAR_NON_NAME_HINTS)
                ):
                    return candidate_clean.upper()

    # Strategy 2: look for all-caps alphabetic lines (name is usually printed in caps)
    for line in lines:
        stripped = re.sub(r"[^A-Za-z\s]", "", line).strip()
        if (
            len(stripped) >= 4
            and stripped.replace(" ", "").isalpha()
            and stripped == stripped.upper()
            and not any(w in stripped for w in AADHAAR_NON_NAME_HINTS)
            and not any(p in stripped for p in skip_patterns)
        ):
            return stripped

    return None


def extract_aadhaar(raw_text: str) -> dict:
    text_upper = raw_text.upper()

    # Extract Aadhaar (last 4 digits)
    aadhaar_match = re.search(r'\d{4}[\s\-]?\d{4}[\s\-]?(\d{4})', raw_text)
    aadhaar_last4 = aadhaar_match.group(1) if aadhaar_match else None

    aadhaar_ok = bool(aadhaar_last4)

    dob = _extract_dob(raw_text)
    age = _calculate_age(dob_ddmmyyyy=dob)
    # If age can't be determined from OCR, don't block — assume eligible
    age_ok = (age is None) or (18 <= age <= 70)

    gender = "Male" if "MALE" in text_upper else ("Female" if "FEMALE" in text_upper else "Other")

    name = _extract_name_from_aadhaar(raw_text)
    mobile_number = extract_mobile_from_aadhaar(raw_text)

    extracted_fields = {
        "aadhaar_last4": aadhaar_last4,
        "mobile_number": mobile_number,
        "mobile_last4": mobile_number[-4:] if mobile_number else None,
        "name": name,
        "date_of_birth": dob,
        "age": age,
        "gender": gender,
        "age_eligible": age_ok,
    }

    missing_fields = [label for key, label in AADHAAR_REQUIRED_FIELDS.items() if not extracted_fields.get(key)]

    return {
        "document_type": "AADHAAR",
        "extracted_fields": extracted_fields,
        "validation": {
            "aadhaar_format_valid": aadhaar_ok,
            "mobile_found": bool(mobile_number),
            "overall_valid": aadhaar_ok and age_ok,
            "missing_fields": missing_fields,
            "required_fields": list(AADHAAR_REQUIRED_FIELDS.values()),
            "issues": [f"{field} is missing" for field in missing_fields],
        },
    }


def cross_validate_kyc(pan_data: dict, aadhaar_data: dict) -> dict:
    pan_name = (pan_data.get("extracted_fields", {}).get("name") or "").strip().upper()
    aadhaar_name = (aadhaar_data.get("extracted_fields", {}).get("name") or "").strip().upper()

    pan_dob = (pan_data.get("extracted_fields", {}).get("date_of_birth") or "").strip()
    aadhaar_dob = (aadhaar_data.get("extracted_fields", {}).get("date_of_birth") or "").strip()
    dob_match = (pan_dob == aadhaar_dob) if (pan_dob and aadhaar_dob) else False

    age_eligible = bool(
        pan_data.get("extracted_fields", {}).get("age_eligible")
        or aadhaar_data.get("extracted_fields", {}).get("age_eligible")
    )

    # Name matching
    if pan_name and aadhaar_name:
        name_score = fuzz.token_sort_ratio(pan_name, aadhaar_name)
    elif pan_name or aadhaar_name:
        # Only one name extracted — treat as partial, don't hard-fail
        name_score = 70
    else:
        # Neither name extracted from OCR — skip name check entirely
        name_score = 85  # assume match, rely on Aadhaar number + age

    # Determine KYC status
    # Pass if: name score acceptable AND (dob matches OR at least one age is eligible)
    if name_score >= 85:
        if dob_match or age_eligible:
            kyc_status = "VERIFIED"
        else:
            kyc_status = "PARTIAL"
    elif name_score >= 60:
        kyc_status = "PARTIAL"
    else:
        kyc_status = "FAILED"

    # overall_kyc_passed: VERIFIED or PARTIAL with age eligible
    overall_passed = (
        kyc_status == "VERIFIED"
        or (kyc_status == "PARTIAL" and age_eligible)
    )

    return {
        "kyc_status": kyc_status,
        "cross_validation": {
            "name_match_score": name_score,
            "dob_match": dob_match,
            "age_eligible": age_eligible,
            "pan_name": pan_name or None,
            "aadhaar_name": aadhaar_name or None,
        },
        "overall_kyc_passed": overall_passed,
    }
