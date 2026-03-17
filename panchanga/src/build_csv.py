"""
build_csv.py
------------
Orchestrate the full pipeline:
    PDF → OCR text files → parsed records → CSV

Usage:
    python src/build_csv.py \
        --pdf "path/to/panchanga.pdf" \
        --output data/processed/karnataka_panchanga_2026.csv

Options:
    --start-page  First PDF page to process (default: 18)
    --end-page    Last PDF page to process (default: 116)
    --skip-ocr    Skip OCR step (reuse existing data/ocr/ files)
"""

import argparse
import csv
from pathlib import Path

from extract import extract
from parse import parse_all

CSV_FIELDS = ["date", "masa", "paksha", "thithi", "thithi_num", "special_day"]


def write_csv(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"\nCSV written: {output_path}  ({len(records)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Build Panchanga CSV from PDF")
    parser.add_argument("--pdf", required=True, help="Path to the Panchanga PDF")
    parser.add_argument("--output", default="data/processed/karnataka_panchanga_2026.csv")
    parser.add_argument("--start-page", type=int, default=18)
    parser.add_argument("--end-page",   type=int, default=116)
    parser.add_argument("--ocr-dir",    default="data/ocr")
    parser.add_argument("--skip-ocr",   action="store_true",
                        help="Skip OCR and use existing text files in --ocr-dir")
    args = parser.parse_args()

    ocr_dir    = Path(args.ocr_dir)
    output_path = Path(args.output)

    # Step 1: OCR
    if not args.skip_ocr:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        print(f"Step 1/2: OCR  (pages {args.start_page}–{args.end_page})")
        extract(str(pdf_path), args.start_page, args.end_page, ocr_dir)
    else:
        print("Step 1/2: OCR  — skipped (using existing files)")

    # Step 2: Parse + write CSV
    print("\nStep 2/2: Parsing OCR text → CSV")
    records = parse_all(ocr_dir)
    write_csv(records, output_path)

    # Quick summary
    print("\nSample rows:")
    for r in records[:5]:
        print(f"  {r['date']}  {r['paksha']:8s}  {r['thithi']:12s}  {r['special_day']}")


if __name__ == "__main__":
    main()
