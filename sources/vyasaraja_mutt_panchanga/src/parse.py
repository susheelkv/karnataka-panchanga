"""
parse.py  —  Vyasaraja Mutt Panchanga
--------------------------------------
TODO: Implement after examining OCR output from the Vyasaraja Mutt PDF.

The parser must produce records with these fields (same contract as ontikoppal):
  date        : ISO-8601 string  e.g. "2026-03-20"
  masa        : English name     e.g. "Chaitra"
  paksha      : "Shukla" | "Krishna"
  thithi      : English name     e.g. "Pratipada"
  thithi_num  : int as string    e.g. "1"
  special_day : festival name or empty string

Entry point expected by build.py:
  from parse import parse_all
  records = parse_all(ocr_dir: Path) -> list[dict]
"""

from pathlib import Path


def parse_all(ocr_dir: Path) -> list[dict]:
    raise NotImplementedError(
        "Vyasaraja Mutt parser not yet implemented. "
        "Run OCR on the PDF first and study the output to build this parser."
    )
