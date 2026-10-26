"""Collect a bounded, source-preserving sample from GovInfo Congressional Record PDFs.

The script downloads official daily-edition PDFs for a fixed date sample, extracts
their text with pypdf, and keeps pages containing direct speaker headings for the
project roster. It never writes generated or paraphrased speech text.
"""

import csv
import os
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

SOURCE_DIR = Path("data/source_pdfs")
TRANSCRIPT_DIR = Path("data/transcripts")
RECORDS_PATH = Path("data/speech_records.csv")
LOCAL_ONLY = os.getenv("LOCAL_ONLY") == "1"

# One issue per month gives coverage across years without downloading the full archive.
DATES = [
    # These dates were selected as regular in-session weekdays; unavailable
    # packages are skipped after PDF-signature validation.
    "2019-01-08", "2019-02-05", "2019-03-05", "2019-04-09",
    "2019-05-07", "2019-06-11", "2019-07-16", "2019-08-06",
    "2019-09-10", "2019-10-15", "2019-11-12", "2019-12-10",
    "2020-01-08", "2020-02-05", "2020-03-03", "2020-04-21",
    "2020-05-12", "2020-06-16", "2020-07-23", "2020-08-06",
    "2020-09-22", "2020-10-01", "2020-11-18", "2020-12-03",
    "2021-01-26", "2021-02-09", "2021-03-16", "2021-04-13",
    "2021-05-11", "2021-06-15", "2021-07-29", "2021-08-10",
    "2021-09-14", "2021-10-19", "2021-11-16", "2021-12-07",
    "2022-01-11", "2022-02-08", "2022-03-15", "2022-04-26",
    "2022-05-17", "2022-06-14", "2022-07-19", "2022-08-02",
    "2022-09-13", "2022-10-18", "2022-11-15", "2022-12-13",
    "2023-01-10", "2023-02-07", "2023-03-14", "2023-04-18",
    "2023-05-16", "2023-06-13", "2023-07-18", "2023-08-01",
    "2023-09-19", "2023-10-17", "2023-11-14", "2023-12-12",
    "2015-01-06", "2015-02-03", "2015-03-03", "2015-04-14",
    "2015-05-12", "2015-06-16", "2015-07-14", "2015-08-04",
    "2015-09-15", "2015-10-20", "2015-11-17", "2015-12-08",
    "2016-01-12", "2016-02-02", "2016-03-15", "2016-04-12",
    "2016-05-10", "2016-06-14", "2016-07-12", "2016-08-02",
    "2016-09-06", "2016-10-18", "2016-11-15", "2016-12-06",
    "2011-01-05", "2011-02-17", "2011-03-03", "2011-04-14",
    "2011-05-12", "2011-06-16", "2011-07-14", "2011-09-08",
    "2012-01-18", "2012-02-16", "2012-03-08", "2012-04-19",
    "2012-05-17", "2012-06-28", "2012-07-19", "2012-09-13",
    "2013-01-03", "2013-02-12", "2013-03-14", "2013-04-18",
    "2013-05-16", "2013-06-27", "2013-07-18", "2013-09-19",
    "2014-01-15", "2014-02-11", "2014-03-13", "2014-04-10",
    "2014-05-15", "2014-06-19", "2014-07-17", "2014-09-16",
    "2011-10-13", "2012-11-13", "2013-10-02", "2014-03-04",
    "2014-12-11",
]

# The heading patterns are deliberately specific for surnames shared by multiple
# members. They match Congressional Record speaker labels, not index or vote lists.
SPEAKERS = {
    "Kevin McCarthy": ("California", [r"Mr\. MCCARTHY\."]),
    "John Cornyn": ("Texas", [r"Mr\. CORNYN\."]),
    "Ted Cruz": ("Texas", [r"Mr\. CRUZ\."]),
    "Marco Rubio": ("Florida", [r"Mr\. RUBIO\."]),
    "Rick Scott": ("Florida", [r"Mr\. SCOTT(?: of Florida)?\."]),
    "Kirsten Gillibrand": ("New York", [r"Ms\. GILLIBRAND\."]),
    "Hakeem Jeffries": ("New York", [r"Mr\. JEFFRIES\."]),
    "Pat Toomey": ("Pennsylvania", [r"Mr\. TOOMEY\."]),
    "Mike Kelly": ("Pennsylvania", [r"Mr\. KELLY(?: of Pennsylvania)?\."]),
    "Tammy Duckworth": ("Illinois", [r"Ms\. DUCKWORTH\."]),
    "David Scott": ("Georgia", [r"Mr\. (?:DAVID )?SCOTT of Georgia\." ]),
    "Hank Johnson": ("Georgia", [r"Mr\. (?:HANK )?JOHNSON of Georgia\." ]),
    "Thom Tillis": ("North Carolina", [r"Mr\. TILLIS\."]),
    "Virginia Foxx": ("North Carolina", [r"Ms\. FOXX\."]),
    "Gary Peters": ("Michigan", [r"Mr\. PETERS\."]),
    "Justin Amash": ("Michigan", [r"Mr\. AMASH\."]),
}


def download_issue(date: str) -> Path | None:
    package = f"CREC-{date}"
    target = SOURCE_DIR / f"{package}.pdf"
    if target.exists():
        if target.read_bytes()[:5] == b"%PDF-":
            return target
        target.unlink()
    if LOCAL_ONLY:
        return None
    url = f"https://www.govinfo.gov/content/pkg/{package}/pdf/{package}.pdf"
    result = subprocess.run(
        ["curl", "-k", "-L", "--fail", "--silent", "--show-error", url, "-o", str(target)],
        check=False,
    )
    if result.returncode:
        target.unlink(missing_ok=True)
        return None
    if target.read_bytes()[:5] != b"%PDF-":
        target.unlink(missing_ok=True)
        return None
    return target


def matching_speakers(text: str) -> list[str]:
    return [
        politician
        for politician, (_, patterns) in SPEAKERS.items()
        if any(re.search(r"(?m)^\s*" + pattern, text) for pattern in patterns)
    ]


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for date in DATES:
        pdf = download_issue(date)
        if not pdf:
            continue
        package = pdf.stem
        reader = PdfReader(str(pdf))
        for page_number, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
            except Exception:
                continue
            for politician in matching_speakers(text):
                record_id = f"{package}-p{page_number:03d}-{politician.lower().replace(' ', '-')}"
                transcript_path = TRANSCRIPT_DIR / f"{record_id}.txt"
                transcript_path.write_text(text, encoding="utf-8")
                rows.append(
                    {
                        "record_id": record_id,
                        "politician": politician,
                        "state": SPEAKERS[politician][0],
                        "date": date,
                        "venue": "Congressional Record floor remarks",
                        "source_type": "Official Congressional Record PDF",
                        "source_url": f"https://www.govinfo.gov/content/pkg/{package}/pdf/{package}.pdf",
                        "source_page": str(page_number),
                        "transcript_path": str(transcript_path),
                        "transcript_status": "PDF text extraction; source-preserved",
                        "text_generated_by_project": "no",
                    }
                )

    # De-duplicate by source page and speaker while preserving deterministic order.
    unique = {row["record_id"]: row for row in rows}
    rows = [unique[key] for key in sorted(unique)]
    with RECORDS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} source-preserved records from {len(set(row['date'] for row in rows))} issues")


if __name__ == "__main__":
    main()

