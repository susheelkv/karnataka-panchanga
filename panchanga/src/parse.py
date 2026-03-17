"""
parse.py
--------
Parse OCR text files (one per PDF page) into structured day records.

Strategy:
  Each day in the Panchanga ends with a "civil thithi" marker:
      ಸಿ.-ವಾ. N ತಿಥಿ    (where N is a Kannada numeral 1–15)
  We split the page text on these markers to get one text block per day,
  then extract thithi and festivals from each block.

Each output record:
    {
        "date":        "2026-03-19",   # ISO date
        "paksha":      "Shukla",       # Shukla or Krishna
        "thithi":      "Pratipada",    # English thithi name
        "thithi_num":  1,              # 1–15 within the paksha
        "special_day": "Ugadi"         # comma-separated, or ""
    }
"""

import re
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Thithi number → English name  (1 = Pratipada … 15 = Purnima / Amavasya)
# ---------------------------------------------------------------------------
THITHI_BY_NUM = {
    1:  "Pratipada",
    2:  "Dvitiya",
    3:  "Tritiya",
    4:  "Chaturthi",
    5:  "Panchami",
    6:  "Shashti",
    7:  "Saptami",
    8:  "Ashtami",
    9:  "Navami",
    10: "Dashami",
    11: "Ekadashi",
    12: "Dvadashi",
    13: "Trayodashi",
    14: "Chaturdashi",
    15: "Purnima",     # Shukla paksha 15
    # Amavasya is also thithi 15 of Krishna paksha — handled by paksha context
}

# Fallback: Kannada abbreviation → (English name, thithi_num)
THITHI_ABBR = {
    "ಪ್ರತಿ":   ("Pratipada",   1),
    "ದ್ವಿತೀ":  ("Dvitiya",     2),
    "ತೃತೀ":    ("Tritiya",     3),
    "ಚತುರ್ಥಿ": ("Chaturthi",   4),
    "ಚತುದ್ಧಿ": ("Chaturthi",   4),
    "ಪಂಚ":     ("Panchami",    5),
    "ಷಷ್ಠೀ":   ("Shashti",     6),
    "ಷಷ್ಠಿ":   ("Shashti",     6),
    "ಸಪ್ತ":    ("Saptami",     7),
    "ಅಷ್ಟ":    ("Ashtami",     8),
    "ನವ":      ("Navami",      9),
    "ದಶ":      ("Dashami",    10),
    "ಏಕಾ":     ("Ekadashi",   11),
    "ದ್ವಾದ":   ("Dvadashi",   12),
    "ದ್ವಾ":    ("Dvadashi",   12),
    "ತ್ರಯೋ":   ("Trayodashi", 13),
    "ಚತುರ್ದ":  ("Chaturdashi",14),
    "ಪೌ":      ("Purnima",    15),
    "ಪೂ":      ("Purnima",    15),
    "ಪೂರ್ಣ":   ("Purnima",    15),
    "ಅಮಾ":     ("Amavasya",   15),
}
THITHI_ABBR_KEYS = sorted(THITHI_ABBR.keys(), key=len, reverse=True)

# ---------------------------------------------------------------------------
# Festival keywords: Kannada substring → English name
# ---------------------------------------------------------------------------
FESTIVAL_MAP = {
    # Use specific compound phrases where possible to avoid false positives
    "ಯುಗಾದಿ ಹಬ್ಬ":     "Ugadi",
    "ಉಗಾದಿ ಹಬ್ಬ":      "Ugadi",
    "ರಾಮನವಮಿ":         "Rama Navami",
    "ಶ್ರೀರಾಮ ನವಮಿ":    "Rama Navami",
    "ಶ್ರೀರಾಮನವಮಿ":     "Rama Navami",
    "ಹನುಮ ಜಯಂತಿ":      "Hanuma Jayanti",
    "ಹನುಮಾನ್ ಜಯಂತಿ":   "Hanuma Jayanti",
    "ಅಕ್ಷಯ ತೃತೀಯ":     "Akshaya Tritiya",
    "ಅಕ್ಷಯ ತೃತೀ":      "Akshaya Tritiya",
    "ಗಣೇಶ ಚತುರ್ಥಿ":    "Ganesha Chaturthi",
    "ಗಣಪತಿ ಚತುರ್ಥಿ":   "Ganesha Chaturthi",
    "ನವರಾತ್ರ":         "Navaratri",
    "ನವರಾತ್ರಾರಂಭ":     "Navaratri Begin",
    "ದಸರ":             "Dasara",
    "ದೀಪಾವಳಿ":         "Deepawali",
    "ದೀಪಾಳಿ":          "Deepawali",
    "ದೀಪೋತ್ಸವ":        "Deepawali",
    "ನರಕ ಚತುರ್ದಶಿ":    "Naraka Chaturdashi",
    "ಮಹಾ ಶಿವರಾತ್ರಿ":   "Maha Shivaratri",  # specific; avoid generic ಶಿವರಾತ್ರಿ (matches Pradosha)
    "ಹೋಳಿ":            "Holi",
    "ಸಂಕ್ರಾಂತಿ":       "Sankranti",
    "ಮಕರ ಸಂಕ್ರಾಂತಿ":   "Makar Sankranti",
    "ವರಮಹಾಲಕ್ಷ್ಮಿ":    "Varamahalakshmi",
    "ಜನ್ಮಾಷ್ಟಮಿ":      "Krishna Janmashtami",
    "ನಾಗ ಪಂಚಮಿ":       "Naga Panchami",
    "ರಥ ಸಪ್ತಮಿ":       "Ratha Saptami",
    "ಬಸವ ಜಯಂತಿ":       "Basava Jayanti",
    "ಅಂಬೇಡ್ಕರ್ ಜಯಂತಿ": "Ambedkar Jayanti",
    "ಡಾ. ಅಂಬೇಡ್ಕರ್":   "Ambedkar Jayanti",
    "ಮಹಾವೀರ ಜಯಂತಿ":    "Mahavir Jayanti",
    "ಅಶೋಕ ಅಷ್ಟಮಿ":     "Ashoka Ashtami",
    "ಅಶೋಕಾಷ್ಟಮೀ":      "Ashoka Ashtami",
    "ಸಂತಾನ ಸಪ್ತಮಿ":    "Santana Saptami",
    "ಕರಗ":             "Bengaluru Karaga",
    "ಗಣೇಶ ಹಬ್ಬ":       "Ganesha Habba",
    "ಶ್ರೀ ಕೃಷ್ಣ ಜನ್ಮಾಷ್ಟಮಿ": "Krishna Janmashtami",
    "ಗೌರಿ ಹಬ್ಬ":       "Gowri Habba",
    "ಗಣೇಶ ಚೌತಿ":       "Ganesha Chaturthi",
    "ಆಯುಧ ಪೂಜೆ":       "Ayudha Puja",
    "ವಿಜಯ ದಶಮಿ":       "Vijayadashami",
    "ದೀಪಾವಳಿ ಅಮಾ":     "Deepawali (Amavasya)",
    "ಬಲಿ ಪಾಡ್ಯಮಿ":     "Bali Padyami",
    "ನಾಗ ಚತುರ್ಥಿ":     "Naga Chaturthi",
    "ಚಂಪಾ ಷಷ್ಠಿ":      "Champa Shashti",
    "ಶ್ರೀ ರಾಮ ಜನ್ಮ":   "Rama Navami",
    # ದ್ವಾದಶ is a thithi name — omitted to avoid false positives
    # ಹುಣ್ಣಿಮೆ / ಅಮಾವಾಸ್ಯ are thithi names, not special festivals — omitted
    "ಕಾರ್ತಿಕ ದೀಪ":     "Karthika Deepa",
    "ತ್ರಿಪುರ ಪೂರ್ಣ":   "Tripura Purnima",
    "ಬೆಂಗಳೂರು ಕರಗ":    "Bengaluru Karaga",
    "ಉಗಾದಿ":           "Ugadi",
}

# ---------------------------------------------------------------------------
# Kannada numeral conversion
# ---------------------------------------------------------------------------
KAN_DIGIT = {"೦": "0", "೧": "1", "೨": "2", "೩": "3", "೪": "4",
             "೫": "5", "೬": "6", "೭": "7", "೮": "8", "೯": "9"}

def _kan_to_int(s: str) -> Optional[int]:
    """Convert a string that may contain Kannada numerals to int."""
    converted = "".join(KAN_DIGIT.get(c, c) for c in s.strip())
    # Keep only digit characters after conversion
    digits = re.sub(r"[^\d]", "", converted)
    try:
        return int(digits) if digits else None
    except ValueError:
        return None

# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

# The header date range: DD-MM-YY : DD-MM-YY
# Separator may be OCR'd as "2" (colon noise) or "|" — allow these exactly
_DATE_LIKE = r"(\d{1,2}[-./]\d{1,2}[-./]\d{2})"
HEADER_DATE_RE = re.compile(_DATE_LIKE + r"\s*[:\|2]\s*" + _DATE_LIKE)

SHUKLA_RE  = re.compile(r"ಶುಕ್ಲ|ಶುಕ್ಷ|ಶ್ಲ|ಶಕ್ಲ")
KRISHNA_RE = re.compile(r"ಕೃಷ್ಣ|ಕ್ರಿಷ್ಣ")

# Kannada masa names → English. Longer keys matched first to catch "Adhika Jyeshtha".
# "ಅಧಿಕ" prefix means intercalary (leap) month.
MASA_MAP: list[tuple[str, str]] = [
    ("ಅಧಿಕ ಜ್ಯೇಷ್ಠ",  "Adhika Jyeshtha"),
    ("ಅಧಿಕ ಜ್ಲೇಷ್ಠ",  "Adhika Jyeshtha"),   # OCR variant
    ("ಅಧಿಕ ಜ್ಯೇಷ",    "Adhika Jyeshtha"),   # truncated variant
    ("ಚೈತ್ರ",         "Chaitra"),
    ("ವೈಶಾಖ",         "Vaishakha"),
    ("ಜ್ಯೇಷ್ಠ",       "Jyeshtha"),
    ("ಜ್ಲೇಷ್ಠ",       "Jyeshtha"),           # OCR variant
    ("ಆಷಾಢ",          "Ashadha"),
    ("ಶ್ರಾವಣ",        "Shravana"),
    ("ಭಾದ್ರಪದ",       "Bhadrapada"),
    ("ಆಶ್ವಯುಜ",       "Ashvayuja"),
    ("ಕಾರ್ತಿಕ",       "Karthika"),
    ("ಮಾರ್ಗಶಿರ",      "Margashira"),
    ("ಪುಷ್ಯ",         "Pushya"),
    ("ಮಾಘ",           "Magha"),
    ("ಫಾಲ್ಗುಣ",       "Phalguna"),
    ("ಫಾಲ್ಕುಣ",       "Phalguna"),           # OCR variant
]

def _fix_ocr_date(s: str) -> Optional[date]:
    """
    Parse 'DD-MM-YY' (or with . / separators) with OCR noise tolerance.
    Handles: month > 12 (e.g. 93 → 3), day > 31 (e.g. 99 → 9).
    """
    s = re.sub(r"[./]", "-", s)
    parts = s.split("-")
    if len(parts) != 3:
        return None
    day_s, mon_s, yr_s = parts
    try:
        day = int(re.sub(r"\D", "", day_s))
        mon = int(re.sub(r"\D", "", mon_s))
        yr  = int(re.sub(r"\D", "", yr_s))
    except ValueError:
        return None
    # Normalize OCR-corrupted day (e.g. 99 → 9, 98 → 8)
    if day > 31:
        day = day % 10
    if day == 0:
        return None
    # Normalize OCR-corrupted month (e.g. 93 → 3, 16 → 6)
    if mon > 12:
        mon = mon % 10
    if mon == 0 or mon > 12:
        return None
    yr += 2000
    try:
        return date(yr, mon, day)
    except ValueError:
        return None

def _parse_header(text: str) -> dict:
    header = "\n".join(text.splitlines()[:3])

    paksha = "Unknown"
    if KRISHNA_RE.search(header):
        paksha = "Krishna"
    elif SHUKLA_RE.search(header):
        paksha = "Shukla"

    masa = "Unknown"
    for kan, eng in MASA_MAP:
        if kan in header:
            masa = eng
            break

    start_date = end_date = None
    m = HEADER_DATE_RE.search(header)
    if m:
        start_date = _fix_ocr_date(m.group(1))
        end_date   = _fix_ocr_date(m.group(2))

    # Post-validation: fix end < start (OCR month off by 1) and span > 20 days (corrupt start)
    if start_date is not None and end_date is not None:
        span = (end_date - start_date).days
        if span < 0:
            # end month likely off by +1 (e.g. Sep instead of Oct)
            try:
                m2 = end_date.month + 1
                y2 = end_date.year + (1 if m2 > 12 else 0)
                m2 = m2 if m2 <= 12 else 1
                end_date = end_date.replace(year=y2, month=m2)
            except ValueError:
                end_date = None
        elif span > 20:
            # start date is corrupt; fall back to end - 14 days
            start_date = end_date - timedelta(days=14)

    return {"paksha": paksha, "masa": masa, "start_date": start_date, "end_date": end_date}

# ---------------------------------------------------------------------------
# Civil thithi marker splitting
# ---------------------------------------------------------------------------

# Pattern: ಸಿ.-ವಾ.  or  ಸಿ-ವಾ.  and known OCR variants.
#
# Marker variants seen in OCR:
#   ಸಿ.-ವಾ.  (standard)
#   ಸಿವಾ.   (no separator — ಿ present)
#   ಸ.-ವಾ.  (no ಿ — i-matra dropped)
#   ಸಿ._ವಾ. (underscore separator)
#   ಸ.--ವಾ. (double dash, no ಿ)
# We require EITHER the i-matra (ಿ) OR at least one separator character
# to avoid matching ಸವಾ inside compound words like ಕೊಠಾರೋತ್ಸವಾರಂಭ.
#
# Thithi extraction is done separately via _extract_thithi_from_window()
# so that the regex never swallows an adjacent marker on the next line.
SIVA_MARKER_RE = re.compile(
    r"ಸ(?:ಿ[._-]*|[._-]+)ವಾ[.']?",
    re.UNICODE
)

# Used by _extract_thithi_from_window to find the stop word in the text window
_THITHI_STOP_RE = re.compile(
    r"(.{0,80}?)(?:ತಿಥಿ|ತಿಥ|BOs|Bs|Sz|SH|SHh|[ತT][ಿi]|ಭು\s*\d)",
    re.UNICODE | re.DOTALL
)

def _extract_thithi_num_from_siva(raw: str) -> Optional[int]:
    """
    Extract the thithi number from the text captured after ಸಿ.-ವಾ.
    Handles:
      - Pure Kannada numerals:  ೧, ೧೦, ೧೫
      - Mixed/noisy OCR:        '೦ (=10), OY (=14), etc.
      - Two-thithi day:         ೮ + ೯  → use first (8)
    """
    # Normalise Kannada numerals to ASCII
    normalized = "".join(KAN_DIGIT.get(c, c) for c in raw)

    # Two-thithi day: "8 + 9" style — take the first number
    two_thithi = re.match(r"\s*(\d+)\s*[+&]\s*(\d+)", normalized)
    if two_thithi:
        return int(two_thithi.group(1))

    # Normal case: first sequence of digits
    m = re.search(r"\d+", normalized)
    if m:
        n = int(m.group())
        if 1 <= n <= 15:
            return n
        # OCR may produce a leading digit sticking to previous: e.g. "10" from "'0"
        # Try last 1-2 digits
        if n > 15:
            n2 = n % 10
            if 1 <= n2 <= 15:
                return n2
    return None

def _extract_thithi_from_window(text: str, pos: int) -> Optional[int]:
    """
    Extract thithi number from the text window starting at pos (right after the marker).
    Looks within the next 2 lines to handle cross-line cases.
    """
    # Take up to 2 lines from pos
    parts = text[pos:].split("\n", 2)
    window = "\n".join(parts[:2])

    # Try to find a thithi stop word and use the text before it
    m = _THITHI_STOP_RE.match(window)
    if m:
        return _extract_thithi_num_from_siva(m.group(1))

    # No stop word found — try extracting a number from the raw window
    return _extract_thithi_num_from_siva(window[:60])


def _split_by_siva_markers(text: str) -> list[dict]:
    """
    Split page text into per-day segments using ಸಿ.-ವಾ. markers.
    Returns list of {thithi_num, text} dicts.
    """
    segments = []
    prev_end = 0

    for m in SIVA_MARKER_RE.finditer(text):
        thithi_num = _extract_thithi_from_window(text, m.end())
        seg_text = text[prev_end : m.end()]
        prev_end = m.end()
        segments.append({"thithi_num": thithi_num, "text": seg_text})

    # Any trailing text after the last marker (belongs to the last day if present)
    # — skip it, it's usually right-column data or footer

    return segments

# ---------------------------------------------------------------------------
# Thithi name resolution
# ---------------------------------------------------------------------------

def _thithi_name(thithi_num: Optional[int], paksha: str, seg_text: str) -> tuple[str, int]:
    """Return (thithi_name, thithi_num), falling back to text-search if needed."""
    if thithi_num is not None and 1 <= thithi_num <= 15:
        name = THITHI_BY_NUM[thithi_num]
        # Override Purnima/Amavasya based on paksha context
        if thithi_num == 15:
            name = "Amavasya" if paksha == "Krishna" else "Purnima"
        return name, thithi_num

    # Fallback: search the segment text for Kannada thithi abbreviations
    for key in THITHI_ABBR_KEYS:
        if key in seg_text:
            return THITHI_ABBR[key]

    return "Unknown", 0

def _advance_paksha(thithi_name: str, current: str) -> str:
    if thithi_name == "Purnima":
        return "Krishna"
    if thithi_name == "Amavasya":
        return "Shukla"
    return current

# ---------------------------------------------------------------------------
# Festival extraction
# ---------------------------------------------------------------------------

def _deduplicate_festivals(festivals: list[str]) -> list[str]:
    """Remove duplicates and suppress generic names when specific ones exist."""
    seen: set[str] = set()
    result: list[str] = []
    # Suppress generic if a more specific variant is present
    suppress = set()
    for f in festivals:
        for other in festivals:
            if other != f and other.startswith(f) and len(other) > len(f):
                suppress.add(f)
    for f in festivals:
        if f not in seen and f not in suppress:
            seen.add(f)
            result.append(f)
    return result

def _find_festivals(text: str) -> list[str]:
    found = []
    for kan, eng in FESTIVAL_MAP.items():
        if kan in text and eng not in found:
            found.append(eng)
    return found

# ---------------------------------------------------------------------------
# Main page parser
# ---------------------------------------------------------------------------

def parse_ocr_file(filepath: Path) -> list[dict]:
    """Parse one OCR text file → list of day records."""
    text = filepath.read_text(encoding="utf-8")
    header = _parse_header(text)

    current_paksha = header["paksha"]
    masa           = header["masa"]
    records: list[dict] = []

    segments = _split_by_siva_markers(text)
    if not segments:
        return []

    end_date   = header["end_date"]
    start_date = header["start_date"]

    # Fallback: if start date couldn't be parsed, estimate from end date
    if start_date is None:
        if end_date is not None:
            start_date = end_date - timedelta(days=14)
        else:
            return []   # Cannot determine date — not a calendar page

    current_date = start_date

    prev_thithi_num = 0

    for seg in segments:
        raw_num = seg["thithi_num"]

        # Sequential fallback: if OCR noise gives us an invalid/duplicate number,
        # use prev + 1 (capped at 15, wrapping back to 1 after Purnima/Amavasya)
        if raw_num is None or raw_num == prev_thithi_num:
            raw_num = (prev_thithi_num % 15) + 1

        thithi_name, thithi_num = _thithi_name(raw_num, current_paksha, seg["text"])
        festivals = _deduplicate_festivals(_find_festivals(seg["text"]))

        records.append({
            "date":        current_date.isoformat(),
            "masa":        masa,
            "paksha":      current_paksha,
            "thithi":      thithi_name,
            "thithi_num":  thithi_num,
            "special_day": ", ".join(festivals),
        })

        prev_thithi_num = thithi_num
        current_paksha = _advance_paksha(thithi_name, current_paksha)
        current_date  += timedelta(days=1)

    return records

# ---------------------------------------------------------------------------
# Batch parse
# ---------------------------------------------------------------------------

def parse_all(ocr_dir: Path) -> list[dict]:
    all_records: list[dict] = []
    files = sorted(ocr_dir.glob("page_*.txt"))
    print(f"Parsing {len(files)} OCR files from {ocr_dir} ...")

    for f in files:
        recs = parse_ocr_file(f)
        if recs:
            print(f"  {f.name}: {len(recs)} days  "
                  f"({recs[0]['date']} → {recs[-1]['date']})")
        all_records.extend(recs)

    # Deduplicate by date (keep first occurrence per date)
    seen: set[str] = set()
    unique: list[dict] = []
    for r in all_records:
        if r["date"] not in seen:
            seen.add(r["date"])
            unique.append(r)

    unique.sort(key=lambda x: x["date"])
    return unique


if __name__ == "__main__":
    import json, sys
    ocr_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ocr")
    records = parse_all(ocr_dir)
    print(json.dumps(records[:20], indent=2, ensure_ascii=False))
    print(f"\nTotal days parsed: {len(records)}")
