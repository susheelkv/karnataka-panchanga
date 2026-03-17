"""
ical_gen.py
-----------
Convert the Panchanga CSV into shareable iCal (.ics) files.

Generates two files:
  • English  — mysore_panchanga_2026_27.ics
  • Kannada  — mysore_panchanga_2026_27_kn.ics

Each day becomes a whole-day event visible in any calendar app
(Apple Calendar, Google Calendar, Outlook, etc.).

Event description format (English example):
  Parabhava Nama Samvatsara
  Vasantha Ruthu
  Chaitra Maasa
  Shukla Paksha, Chaturthi (4)
  Festival: Ugadi          ← only when applicable

Usage:
    python src/ical_gen.py \
        --csv  data/processed/karnataka_panchanga_2026_27.csv \
        --out  data/processed/mysore_panchanga_2026_27.ics
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from icalendar import Calendar, Event, vText

PRODID    = "-//Ganesha Project//Mysore Panchanga//EN"
TIMEZONE  = "Asia/Kolkata"

# ── Samvatsara name ────────────────────────────────────────────────────────────
SAMVATSARA_EN = "Parabhava Nama Samvatsara"
SAMVATSARA_KN = "ಪರಾಭವ ನಾಮ ಸಂವತ್ಸರ"

# ── Ruthu (season) maps ────────────────────────────────────────────────────────
RUTHU_EN: dict[str, str] = {
    "Chaitra":          "Vasantha",
    "Vaishakha":        "Vasantha",
    "Jyeshtha":         "Grishma",
    "Adhika Jyeshtha":  "Grishma",
    "Ashadha":          "Grishma",
    "Shravana":         "Varsha",
    "Bhadrapada":       "Varsha",
    "Ashvayuja":        "Sharad",
    "Karthika":         "Sharad",
    "Margashira":       "Hemanta",
    "Pushya":           "Hemanta",
    "Magha":            "Shishira",
    "Phalguna":         "Shishira",
}

RUTHU_KN: dict[str, str] = {
    "Chaitra":          "ವಸಂತ",
    "Vaishakha":        "ವಸಂತ",
    "Jyeshtha":         "ಗ್ರೀಷ್ಮ",
    "Adhika Jyeshtha":  "ಗ್ರೀಷ್ಮ",
    "Ashadha":          "ಗ್ರೀಷ್ಮ",
    "Shravana":         "ವರ್ಷ",
    "Bhadrapada":       "ವರ್ಷ",
    "Ashvayuja":        "ಶರದ್",
    "Karthika":         "ಶರದ್",
    "Margashira":       "ಹೇಮಂತ",
    "Pushya":           "ಹೇಮಂತ",
    "Magha":            "ಶಿಶಿರ",
    "Phalguna":         "ಶಿಶಿರ",
}

# ── Maasa (month) Kannada names ────────────────────────────────────────────────
MASA_KN: dict[str, str] = {
    "Chaitra":          "ಚೈತ್ರ",
    "Vaishakha":        "ವೈಶಾಖ",
    "Jyeshtha":         "ಜ್ಯೇಷ್ಠ",
    "Adhika Jyeshtha":  "ಅಧಿಕ ಜ್ಯೇಷ್ಠ",
    "Ashadha":          "ಆಷಾಢ",
    "Shravana":         "ಶ್ರಾವಣ",
    "Bhadrapada":       "ಭಾದ್ರಪದ",
    "Ashvayuja":        "ಆಶ್ವಯುಜ",
    "Karthika":         "ಕಾರ್ತಿಕ",
    "Margashira":       "ಮಾರ್ಗಶಿರ",
    "Pushya":           "ಪುಷ್ಯ",
    "Magha":            "ಮಾಘ",
    "Phalguna":         "ಫಾಲ್ಗುಣ",
}

# ── Paksha Kannada names ───────────────────────────────────────────────────────
PAKSHA_KN: dict[str, str] = {
    "Shukla":  "ಶುಕ್ಲ",
    "Krishna": "ಕೃಷ್ಣ",
}

# ── Thithi Kannada names ───────────────────────────────────────────────────────
THITHI_KN: dict[str, str] = {
    "Pratipada":   "ಪ್ರತಿಪದ",
    "Dvitiya":     "ದ್ವಿತೀಯ",
    "Tritiya":     "ತೃತೀಯ",
    "Chaturthi":   "ಚತುರ್ಥಿ",
    "Panchami":    "ಪಂಚಮಿ",
    "Shashti":     "ಷಷ್ಠಿ",
    "Saptami":     "ಸಪ್ತಮಿ",
    "Ashtami":     "ಅಷ್ಟಮಿ",
    "Navami":      "ನವಮಿ",
    "Dashami":     "ದಶಮಿ",
    "Ekadashi":    "ಏಕಾದಶಿ",
    "Dvadashi":    "ದ್ವಾದಶಿ",
    "Trayodashi":  "ತ್ರಯೋದಶಿ",
    "Chaturdashi": "ಚತುರ್ದಶಿ",
    "Purnima":     "ಪೂರ್ಣಿಮೆ",
    "Amavasya":    "ಅಮಾವಾಸ್ಯೆ",
}


# ── Event builders ─────────────────────────────────────────────────────────────

def _summary_en(paksha: str, thithi: str, special_day: str) -> str:
    thithi_part = f"{paksha} · {thithi}"
    if special_day:
        return f"{special_day}  |  {thithi_part}"
    return thithi_part


def _summary_kn(paksha: str, thithi: str, special_day: str) -> str:
    p = PAKSHA_KN.get(paksha, paksha)
    t = THITHI_KN.get(thithi, thithi)
    thithi_part = f"{p} · {t}"
    if special_day:
        return f"{special_day}  |  {thithi_part}"
    return thithi_part


def _description_en(masa: str, paksha: str, thithi: str, thithi_num: str, special_day: str) -> str:
    ruthu = RUTHU_EN.get(masa, "")
    lines = [
        SAMVATSARA_EN,
        f"{ruthu} Ruthu",
        f"{masa} Maasa",
        f"{paksha} Paksha, {thithi} ({thithi_num})",
    ]
    if special_day:
        lines.append(f"Festival: {special_day}")
    return "\n".join(lines)


def _description_kn(masa: str, paksha: str, thithi: str, thithi_num: str, special_day: str) -> str:
    ruthu = RUTHU_KN.get(masa, "")
    masa_kn   = MASA_KN.get(masa, masa)
    paksha_kn = PAKSHA_KN.get(paksha, paksha)
    thithi_kn = THITHI_KN.get(thithi, thithi)
    lines = [
        SAMVATSARA_KN,
        f"{ruthu} ಋತು",
        f"{masa_kn} ಮಾಸ",
        f"{paksha_kn} ಪಕ್ಷ, {thithi_kn} ({thithi_num})",
    ]
    if special_day:
        lines.append(f"ಹಬ್ಬ: {special_day}")
    return "\n".join(lines)


# ── Calendar builder ───────────────────────────────────────────────────────────

def build_ical(records: list[dict], cal_name: str, cal_desc: str, lang: str) -> Calendar:
    """
    lang: "en" | "kn"
    """
    cal = Calendar()
    cal.add("prodid",        vText(PRODID))
    cal.add("version",       "2.0")
    cal.add("calscale",      "GREGORIAN")
    cal.add("method",        "PUBLISH")
    cal.add("x-wr-calname",  vText(cal_name))
    cal.add("x-wr-caldesc",  vText(cal_desc))
    cal.add("x-wr-timezone", vText(TIMEZONE))

    summary_fn     = _summary_en     if lang == "en" else _summary_kn
    description_fn = _description_en if lang == "en" else _description_kn

    for row in records:
        try:
            day = date.fromisoformat(row["date"])
        except ValueError:
            continue

        masa       = row.get("masa", "")
        paksha     = row.get("paksha", "")
        thithi     = row.get("thithi", "")
        thithi_num = row.get("thithi_num", "")
        special    = row.get("special_day", "")

        event = Event()
        event.add("uid",         vText(f"{row['date']}-panchanga-{lang}@ganesha-project"))
        event.add("summary",     vText(summary_fn(paksha, thithi, special)))
        event.add("description", vText(description_fn(masa, paksha, thithi, thithi_num, special)))
        event.add("dtstart",     day)   # whole-day (no time component)
        event.add("dtend",       day)   # same date = all-day in iCal spec
        event.add("transp",      vText("TRANSPARENT"))
        cal.add_component(event)

    return cal


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate iCal from Panchanga CSV")
    parser.add_argument("--csv", default="data/processed/karnataka_panchanga_2026_27.csv")
    parser.add_argument("--out", default="data/processed/mysore_panchanga_2026_27.ics",
                        help="Path for English .ics; Kannada file gets _kn suffix automatically")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print(f"Read {len(records)} rows from {csv_path.name}")

    out_en = Path(args.out)
    out_kn = out_en.with_stem(out_en.stem + "_kn")

    configs = [
        (
            out_en, "en",
            "Mysore Panchanga 2026-27 (Sri Parabhava Nama Samvatsara)",
            "Daily Hindu calendar (thithi, paksha, festivals) for Karnataka, India. "
            "Source: Ontikoppal Panchanga Mandira, Mysore.",
        ),
        (
            out_kn, "kn",
            "ಮೈಸೂರು ಪಂಚಾಂಗ 2026-27 (ಶ್ರೀ ಪರಾಭವ ನಾಮ ಸಂವತ್ಸರ)",
            "ಕರ್ನಾಟಕದ ದಿನನಿತ್ಯದ ಹಿಂದೂ ಪಂಚಾಂಗ (ತಿಥಿ, ಪಕ್ಷ, ಹಬ್ಬಗಳು). "
            "ಮೂಲ: ಒಂಟಿಕೊಪ್ಪಲ್ ಪಂಚಾಂಗ ಮಂದಿರ, ಮೈಸೂರು.",
        ),
    ]

    for out_path, lang, cal_name, cal_desc in configs:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cal = build_ical(records, cal_name, cal_desc, lang)
        out_path.write_bytes(cal.to_ical())
        print(f"[{lang}] {out_path}  ({out_path.stat().st_size // 1024} KB, {len(records)} events)")


if __name__ == "__main__":
    main()
