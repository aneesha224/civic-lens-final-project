"""Add canonical GovInfo HTML-page candidates to the speech records.

The existing transcript files remain unchanged. This script adds a direct
machine-readable source URL derived from the page label printed in the official
Congressional Record PDF extraction.
"""

import csv
import re
from pathlib import Path

RECORDS_PATH = Path("data/speech_records.csv")
HEADER_RE = re.compile(
    r"CONGRESSIONAL RECORD.*?(HOUSE|SENATE|Extensions of Remarks)\s*([HSE]\d+)"
)


def page_label(transcript_path: str) -> str | None:
    text = Path(transcript_path).read_text(encoding="utf-8")
    match = HEADER_RE.search(text)
    if not match:
        return None
    return match.group(2)


def main() -> None:
    rows = list(csv.DictReader(RECORDS_PATH.open(encoding="utf-8")))
    for row in rows:
        package = f"CREC-{row['date']}"
        label = page_label(row["transcript_path"])
        row["govinfo_html_candidate_url"] = ""
        if label:
            row["govinfo_html_candidate_url"] = (
                f"https://www.govinfo.gov/content/pkg/{package}/html/"
                f"{package}-pt1-Pg{label}.htm"
            )
        row["source_format"] = "PDF extraction with GovInfo HTML source link"

    with RECORDS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Added GovInfo HTML links to {len(rows)} records")


if __name__ == "__main__":
    main()

