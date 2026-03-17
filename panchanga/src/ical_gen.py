"""
ical_gen.py
-----------
Convert the Panchanga CSV into a shareable iCal (.ics) file.

Each day becomes a whole-day event visible in any calendar app
(Apple Calendar, Google Calendar, Outlook, etc.).

Event title examples:
  • "Shukla · Pratipada"
  • "Ugadi  |  Shukla · Pratipada"

Usage:
    python src/ical_gen.py \
        --csv  data/processed/karnataka_panchanga_2026_27.csv \
        --out  data/processed/mysore_panchanga_2026_27.ics \
        [--name "Mysore Panchanga 2026-27"]
"""

import argparse
import csv
from datetime import date
from pathlib import Path
from uuid import uuid4

from icalendar import Calendar, Event, vText

# Calendar metadata
DEFAULT_CAL_NAME    = "Mysore Panchanga 2026-27 (Sri Parabhavanama Samvatsara)"
DEFAULT_CAL_DESC    = (
    "Daily Hindu calendar (thithi, paksha, festivals) for Karnataka, India. "
    "Source: Ontikoppal Panchanga Mandira, Mysore. All times are India Standard Time (IST)."
)
PRODID = "-//Ganesha Project//Mysore Panchanga//EN"
TIMEZONE = "Asia/Kolkata"   # IST — MVP uses India time only

# Ruthu (season) for each Masa. Two consecutive masas share the same ruthu.
RUTHU_MAP: dict[str, str] = {
    "Chaitra":          "Vasantha",   # Spring
    "Vaishakha":        "Vasantha",
    "Jyeshtha":         "Grishma",    # Summer
    "Adhika Jyeshtha":  "Grishma",
    "Ashadha":          "Grishma",
    "Shravana":         "Varsha",     # Monsoon
    "Bhadrapada":       "Varsha",
    "Ashvayuja":        "Sharad",     # Autumn
    "Karthika":         "Sharad",
    "Margashira":       "Hemanta",    # Pre-winter
    "Pushya":           "Hemanta",
    "Magha":            "Shishira",   # Winter
    "Phalguna":         "Shishira",
}


def _event_summary(paksha: str, thithi: str, special_day: str) -> str:
    """Festival leads the title when present; otherwise just paksha · thithi."""
    thithi_part = f"{paksha} · {thithi}"
    if special_day:
        return f"{special_day}  |  {thithi_part}"
    return thithi_part


def _event_description(masa: str, paksha: str, thithi: str, thithi_num: str, special_day: str) -> str:
    ruthu = RUTHU_MAP.get(masa, "")
    lines = [
        f"Ruthu:   {ruthu}",
        f"Maasa:   {masa}",
        f"Paksha:  {paksha}",
        f"Thithi:  {thithi} ({thithi_num})",
    ]
    if special_day:
        lines.append(f"Festival: {special_day}")
    # lines.append("Source: Ontikoppal Panchanga Mandira, Mysore (Karnataka Panchanga)")
    return "\n".join(lines)


def build_ical(records: list[dict], cal_name: str, cal_desc: str) -> Calendar:
    cal = Calendar()
    cal.add("prodid", vText(PRODID))
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", vText(cal_name))
    cal.add("x-wr-caldesc", vText(cal_desc))
    cal.add("x-wr-timezone", vText(TIMEZONE))

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
        event.add("uid",      vText(f"{row['date']}-panchanga@ganesha-project"))
        event.add("summary",  vText(_event_summary(paksha, thithi, special)))
        event.add("description", vText(_event_description(masa, paksha, thithi, thithi_num, special)))
        event.add("dtstart",  day)          # whole-day event (no time component)
        event.add("dtend",    day)          # same day = all-day in iCal spec
        event.add("transp",   vText("TRANSPARENT"))  # show as free, not busy
        cal.add_component(event)

    return cal


def main():
    parser = argparse.ArgumentParser(description="Generate iCal from Panchanga CSV")
    parser.add_argument("--csv",  default="data/processed/karnataka_panchanga_2026_27.csv")
    parser.add_argument("--out",  default="data/processed/mysore_panchanga_2026_27.ics")
    parser.add_argument("--name", default=DEFAULT_CAL_NAME)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print(f"Read {len(records)} rows from {csv_path.name}")

    cal = build_ical(records, args.name, DEFAULT_CAL_DESC)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(cal.to_ical())
    print(f"iCal written: {out_path}  ({out_path.stat().st_size // 1024} KB)")
    print(f"Events: {len(records)}")
    print()
    print("How to share:")
    print("  • Add to Apple Calendar: File → Import → select the .ics file")
    print("  • Subscribe via URL:     host the .ics file and share the URL")
    print("  • Google Calendar:       Settings → Add calendar → From URL / Import")


if __name__ == "__main__":
    main()
