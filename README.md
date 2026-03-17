# Mysore Panchanga 2026-27

Daily Hindu calendar (thithi, paksha, masa, ruthu, festivals) for Karnataka, India.

**Samvatsara:** Sri Parabhavanama (19 March 2026 – 6 April 2027)
**Source:** Ontikoppal Panchanga Mandira, Mysore

## Subscribe to the Calendar

| App | Instructions |
|-----|-------------|
| **Apple Calendar** | File → New Calendar Subscription → paste URL below |
| **Google Calendar** | Settings → Add calendar → From URL → paste URL below |
| **Outlook** | Add calendar → From internet → paste URL below |

**Subscription URL:**
```
https://susheelkv.github.io/mysore-panchanga/mysore_panchanga_2026_27.ics
```

Each day shows:
- **Title:** Festival name (if any) and Paksha · Thithi — e.g. *Ugadi  |  Shukla · Pratipada*
- **Details (on click):** Ruthu, Maasa, Paksha, Thithi number, Festival

## Coverage

358 of 384 days covered (93.2%). Gaps of 1–4 days at a few page boundaries in the source PDF due to OCR noise.

## How It Was Built

```
panchanga/
  src/
    extract.py    # PDF → OCR text (pytesseract, 300 DPI, Kannada + English)
    parse.py      # OCR text → structured records
    build_csv.py  # orchestrates pipeline → CSV
    ical_gen.py   # CSV → .ics calendar file
  data/
    processed/    # karnataka_panchanga_2026_27.csv  +  mysore_panchanga_2026_27.ics
```

```bash
cd panchanga
pip install -r requirements.txt
python src/build_csv.py --pdf "../SRI PARABHAVANAMA SAMVATSARA.pdf" \
    --start-page 18 --end-page 43 \
    --output data/processed/karnataka_panchanga_2026_27.csv
python src/ical_gen.py
```
