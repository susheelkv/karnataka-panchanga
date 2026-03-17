# Ganesha Project — Hindu Panchanga Calendars

Shareable iCal calendars derived from traditional Karnataka panchanga PDFs.

## Calendars

| Source | Samvatsara | Subscribe |
|--------|-----------|-----------|
| Ontikoppal Panchanga Mandira, Mysore | Sri Parabhava Nama (2026–27) | [Landing page](https://susheelkv.github.io/mysore-ontikoppal-panchanga/) |
| Vyasaraja Mutt Panchanga | Sri Parabhava Nama (2026–27) | *(coming soon)* |

## Repository structure

```
ganesha-project/
  shared/                           # Reusable pipeline code (all sources)
    extract.py                      # PDF → OCR text  (pytesseract, 300 DPI)
    ical_gen.py                     # CSV → .ics calendar (English + Kannada)

  sources/
    ontikoppal_panchanga/           # Ontikoppal Panchanga Mandira, Mysore
      src/
        parse.py                    # Ontikoppal-specific OCR parser
        build.py                    # Pipeline orchestrator
      data/
        ocr/                        # page_018.txt … page_043.txt  (.gitignored)
        processed/                  # CSV + .ics output files

    vyasaraja_mutt_panchanga/       # Vyasaraja Mutt Panchanga  (in progress)
      src/
        parse.py                    # TODO: implement after examining OCR output
        build.py                    # Pipeline orchestrator
      data/
        ocr/                        # .gitignored
        processed/

  docs/                             # GitHub Pages
    index.html                      # Calendar landing page
    mysore_panchanga_2026_27.ics    # Ontikoppal — English
    mysore_panchanga_2026_27_kn.ics # Ontikoppal — Kannada

  requirements.txt
```

## Running the Ontikoppal pipeline

```bash
source .venv/bin/activate
cd sources/ontikoppal_panchanga

# Full pipeline (OCR + parse + CSV)
python src/build.py \
    --pdf "../../SRI PARABHAVANAMA SAMVATSARA (19.03.2026 TO 06.04.2027).pdf" \
    --output data/processed/karnataka_panchanga_2026_27.csv

# Re-parse only (OCR already done)
python src/build.py --skip-ocr \
    --ocr-dir data/ocr \
    --output data/processed/karnataka_panchanga_2026_27.csv

# Generate iCal (English + Kannada)
cd ../..
python shared/ical_gen.py \
    --csv sources/ontikoppal_panchanga/data/processed/karnataka_panchanga_2026_27.csv \
    --out sources/ontikoppal_panchanga/data/processed/mysore_panchanga_2026_27.ics
```

## Coverage

Ontikoppal 2026-27: 358 of 384 days (93.2%).
Gaps of 1–4 days at a few page boundaries due to OCR noise.

## Data sources

- **Ontikoppal Panchanga Mandira, Mysore** — one of Karnataka's most respected traditional panchanga publishers
- **Vyasaraja Mutt Panchanga** — Uttaradi Math, Bengaluru
