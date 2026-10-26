"""Import verified, source-preserved campaign transcripts.

Place a manifest at data/campaign_speeches/manifest.csv and exact transcript
files in data/campaign_speeches/transcripts/, then run this script from the
Final Project directory. The importer refuses missing files and invalid URLs.
It never generates or rewrites transcript text.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import SpeechRecord


ROOT = Path("data/campaign_speeches")
MANIFEST = ROOT / "manifest.csv"
OUTPUT = Path("data/campaign_speech_records.csv")


def main() -> None:
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing {MANIFEST}")
    rows: list[dict[str, str]] = []
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            transcript = ROOT / raw["transcript_path"]
            if not transcript.is_file():
                raise SystemExit(f"Missing transcript: {transcript}")
            parsed = urlparse(raw["source_url"])
            if parsed.scheme not in {"http", "https"}:
                raise SystemExit(f"Invalid source URL: {raw['source_url']}")
            row = {
                **raw,
                "source_category": "campaign",
                "source_page_start": raw.get("source_page_start") or None,
                "source_page_end": raw.get("source_page_end") or None,
                "page_count": raw.get("page_count") or None,
                "transcript_status": raw.get("transcript_status", "verified source copy"),
                "boundary_status": raw.get("boundary_status", "source-defined"),
                "text_generated_by_project": "no",
            }
            SpeechRecord.model_validate(row)
            rows.append(row)
    fields = list(rows[0].keys()) if rows else [
        "record_id", "politician", "state", "date", "venue", "source_type",
        "source_category", "source_url", "source_page_start", "source_page_end",
        "page_count", "transcript_path", "transcript_status", "boundary_status",
        "text_generated_by_project",
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} campaign speech records")


if __name__ == "__main__":
    main()
