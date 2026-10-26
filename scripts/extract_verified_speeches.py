"""Extract selected pages from a downloaded official Congressional Record PDF.

The speech text is copied from the source PDF by pypdf. This script does not
summarize, rewrite, clean up, or generate transcript text.
"""

import csv
from pathlib import Path

from pypdf import PdfReader

SOURCE_ID = "CREC-2020-01-08"
SOURCE_URL = "https://www.govinfo.gov/content/pkg/CREC-2020-01-08/pdf/CREC-2020-01-08.pdf"
SOURCE_PDF = Path("data/source_pdfs/CREC-2020-01-08.pdf")
OUTPUT_DIR = Path("data/transcripts")
OUTPUT_CSV = Path("data/speech_records.csv")

# These pages were manually checked in the official PDF as direct floor
# remarks. Page numbers are one-based PDF pages, not invented titles.
SELECTED_PAGES = {
    22: ("Hakeem Jeffries", "New York", "House floor remarks"),
    55: ("Tammy Duckworth", "Illinois", "Senate floor remarks"),
    59: ("John Cornyn", "Texas", "Senate floor remarks"),
}


def main() -> None:
    if not SOURCE_PDF.exists():
        raise SystemExit(f"Missing source PDF: {SOURCE_PDF}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(SOURCE_PDF))
    rows = []

    for page_number, (politician, state, venue) in SELECTED_PAGES.items():
        page_text = reader.pages[page_number - 1].extract_text() or ""
        if not page_text.strip():
            raise SystemExit(f"No extractable text on PDF page {page_number}")

        record_id = f"{SOURCE_ID}-p{page_number:03d}"
        transcript_path = OUTPUT_DIR / f"{record_id}.txt"
        transcript_path.write_text(page_text, encoding="utf-8")
        rows.append(
            {
                "record_id": record_id,
                "politician": politician,
                "state": state,
                "date": "2020-01-08",
                "venue": venue,
                "source_type": "Official Congressional Record PDF",
                "source_url": SOURCE_URL,
                "source_page": str(page_number),
                "transcript_path": str(transcript_path),
                "transcript_status": "PDF text extraction; source-preserved",
                "text_generated_by_project": "no",
            }
        )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} source-preserved speech records to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

