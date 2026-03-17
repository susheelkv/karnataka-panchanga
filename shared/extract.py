"""
extract.py
----------
Convert PDF calendar pages to OCR text files.

Usage:
    python src/extract.py --pdf <path_to_pdf> [--start-page 18] [--end-page 116]

Outputs one .txt file per page into data/ocr/.
"""

import argparse
import os
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Calendar data starts at PDF page 18 (based on manual inspection)
DEFAULT_START_PAGE = 18
DEFAULT_END_PAGE = 116
DPI = 300  # High enough for clean Kannada OCR
TESS_LANG = "kan+eng"
TESS_CONFIG = "--psm 6"  # Assume a single uniform block of text


def ocr_page(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang=TESS_LANG, config=TESS_CONFIG)


def extract(pdf_path: str, start_page: int, end_page: int, ocr_dir: Path) -> None:
    ocr_dir.mkdir(parents=True, exist_ok=True)
    total = end_page - start_page + 1

    for i, pdf_page_num in enumerate(range(start_page, end_page + 1), 1):
        out_file = ocr_dir / f"page_{pdf_page_num:03d}.txt"
        if out_file.exists():
            print(f"  [{i}/{total}] page {pdf_page_num} — already extracted, skipping")
            continue

        print(f"  [{i}/{total}] page {pdf_page_num} — converting + OCR...", end=" ", flush=True)
        images = convert_from_path(pdf_path, first_page=pdf_page_num, last_page=pdf_page_num, dpi=DPI)
        text = ocr_page(images[0])
        out_file.write_text(text, encoding="utf-8")
        print("done")

    print(f"\nOCR complete. {total} pages written to {ocr_dir}")


def main():
    parser = argparse.ArgumentParser(description="Extract OCR text from Panchanga PDF pages")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE)
    parser.add_argument("--end-page", type=int, default=DEFAULT_END_PAGE)
    parser.add_argument("--ocr-dir", default="data/ocr", help="Output directory for OCR text files")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    ocr_dir = Path(args.ocr_dir)
    print(f"Extracting pages {args.start_page}–{args.end_page} from {pdf_path.name}")
    extract(str(pdf_path), args.start_page, args.end_page, ocr_dir)


if __name__ == "__main__":
    main()
