"""Reconstruct complete Congressional Record speaker turns from issue PDFs.

The earlier collection pass kept only individual pages that contained a target
speaker heading. This script reads each downloaded issue in page order and
follows a target speaker's text until the next Congressional Record speaker
heading, including continuation pages. The output remains an exact extraction
from the official PDF; it is not generated or paraphrased text.

Run from the Final Project directory:

    python scripts/reconstruct_complete_remarks.py

The script intentionally writes a new corpus so the earlier page-level data is
preserved for comparison and provenance audits.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


SOURCE_DIR = Path("data/source_pdfs")
OUTPUT_DIR = Path("data/complete_remarks")
OUTPUT_CSV = Path("data/complete_speech_records.csv")

# These patterns match the speaker labels used by the current source corpus.
# Whitespace is allowed inside an extracted uppercase surname because older PDF
# text extraction sometimes separates letters (for example, "C ORNYN").
SPEAKERS: dict[str, tuple[str, list[str]]] = {
    "Kevin McCarthy": ("California", [r"M(?:r)?\.?\s*(?:KEVIN\s*)?M\s*C\s*CARTHY\."]),
    "John Cornyn": ("Texas", [r"M(?:r)?\.?\s*(?:JOHN\s*)?C\s*O\s*R\s*N\s*Y\s*N\."]),
    "Ted Cruz": ("Texas", [r"M(?:r)?\.?\s*(?:TED\s*)?C\s*R\s*U\s*Z\."]),
    "Marco Rubio": ("Florida", [r"M(?:r)?\.?\s*(?:MARCO\s*)?R\s*U\s*B\s*I\s*O\."]),
    "Rick Scott": ("Florida", [r"M(?:r)?\.?\s*(?:RICK\s*)?S\s*C\s*O\s*T\s*T(?:\s+of\s+Florida)?\."]),
    "Kirsten Gillibrand": ("New York", [r"(?:Ms|Mrs)\.?\s*(?:KIRSTEN\s*)?G\s*I\s*L\s*L\s*I\s*B\s*R\s*A\s*N\s*D\."]),
    "Hakeem Jeffries": ("New York", [r"M(?:r)?\.?\s*(?:HAKEEM\s*)?J\s*E\s*F\s*F\s*R\s*I\s*E\s*S\."]),
    "Pat Toomey": ("Pennsylvania", [r"M(?:r)?\.?\s*(?:PAT\s*)?T\s*O\s*O\s*M\s*E\s*Y\."]),
    "Mike Kelly": ("Pennsylvania", [r"M(?:r)?\.?\s*(?:MIKE\s*)?K\s*E\s*L\s*L\s*Y(?:\s+of\s+Pennsylvania)?\."]),
    "Tammy Duckworth": ("Illinois", [r"Ms\.?\s*(?:TAMMY\s*)?D\s*U\s*C\s*K\s*W\s*O\s*R\s*T\s*H\."]),
    "David Scott": ("Georgia", [r"M(?:r)?\.?\s*(?:DAVID\s*)?S\s*C\s*O\s*T\s*T\s+of\s+Georgia\."]),
    "Hank Johnson": ("Georgia", [r"M(?:r)?\.?\s*(?:HANK\s*)?J\s*O\s*H\s*N\s*S\s*O\s*N\s+of\s+Georgia\."]),
    "Thom Tillis": ("North Carolina", [r"M(?:r)?\.?\s*(?:THOM\s*)?T\s*I\s*L\s*L\s*I\s*S\."]),
    "Virginia Foxx": ("North Carolina", [r"(?:Ms|Mrs)\.?\s*(?:VIRGINIA\s*)?F\s*O\s*X\s*X\."]),
    "Gary Peters": ("Michigan", [r"M(?:r)?\.?\s*(?:GARY\s*)?P\s*E\s*T\s*E\s*R\s*S\."]),
    "Justin Amash": ("Michigan", [r"M(?:r)?\.?\s*(?:JUSTIN\s*)?A\s*M\s*A\s*S\s*H\."]),
}

# Congressional Record headings may include a district label, such as
# "Mr. LEWIS of California." The line-start requirement avoids most ordinary
# prose; recognizing mixed case is necessary for those district labels.
NEXT_SPEAKER = re.compile(
    r"(?m)^\s*(?:Mr|Ms|Mrs|Miss)\.\s+[A-Z][A-Za-z .'-]{1,80}\.(?:\s|$)"
)
NON_REMARK_SECTION = re.compile(
    r"(?m)^\s*(?:PROCEEDINGS OF THE|BILLS PRESENTED TO THE|"
    r"EXECUTIVE COMMUNICATIONS|ADDITIONAL STATEMENTS|"
    r"PUBLIC BILLS AND RESOLUTIONS|PETITIONS(?:, ETC\.)?|"
    r"MESSAGES FROM THE|NOMINATIONS?|NOMINATION OF|"
    r"REPORTS OF COMMITTEES|AMENDMENTS(?: EN BLOC)?)[A-Z0-9 ,.'()\-]*$"
)


@dataclass(frozen=True)
class Occurrence:
    politician: str
    start: int
    end: int


def target_occurrences(text: str) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for politician, (_, patterns) in SPEAKERS.items():
        for pattern in patterns:
            for match in re.finditer(r"(?m)^\s*" + pattern, text):
                occurrences.append(Occurrence(politician, match.start(), match.end()))
    return sorted(occurrences, key=lambda occurrence: occurrence.start)


def next_boundary(text: str, position: int) -> int | None:
    matches = [
        match.start()
        for expression in (NEXT_SPEAKER, NON_REMARK_SECTION)
        if (match := expression.search(text, position))
    ]
    return min(matches) if matches else None


def extract_remark(pages: list[str], start_page: int, start_offset: int) -> tuple[str, int, str]:
    """Return text, inclusive ending page, and boundary status."""
    chunks = [pages[start_page][start_offset:]]
    for page_number in range(start_page, len(pages)):
        search_from = start_offset + 1 if page_number == start_page else 0
        boundary = next_boundary(pages[page_number], search_from)
        if boundary is not None:
            if page_number == start_page:
                chunks[0] = pages[page_number][start_offset:boundary]
            else:
                chunks.append(pages[page_number][:boundary])
            status = (
                "next_speaker_or_section_boundary"
                if NON_REMARK_SECTION.match(pages[page_number][boundary:])
                else "next_speaker_heading"
            )
            return "\n".join(chunks).strip(), page_number + 1, status
        if page_number > start_page:
            chunks.append(pages[page_number])
    return "\n".join(chunks).strip(), len(pages), "end_of_issue"


def issue_date(package: str) -> str:
    return package.removeprefix("CREC-")


def clean_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main() -> None:
    pdfs = sorted(SOURCE_DIR.glob("CREC-*.pdf"))
    if not pdfs:
        raise SystemExit(f"No source PDFs found in {SOURCE_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    skipped: list[str] = []
    for pdf_path in pdfs:
        package = pdf_path.stem
        if pdf_path.read_bytes()[:5] != b"%PDF-":
            skipped.append(f"{pdf_path.name} (invalid PDF signature)")
            continue
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as error:
            skipped.append(f"{pdf_path.name} ({error})")
            continue
        pages = [(page.extract_text() or "") for page in reader.pages]

        starts: list[tuple[int, Occurrence]] = []
        for page_number, text in enumerate(pages):
            starts.extend((page_number, occurrence) for occurrence in target_occurrences(text))

        for sequence, (page_number, occurrence) in enumerate(starts, start=1):
            text, end_page, boundary_status = extract_remark(
                pages, page_number, occurrence.start
            )
            if not text:
                continue
            date = issue_date(package)
            record_id = (
                f"{package}-remark-{sequence:03d}-"
                f"{clean_id(occurrence.politician)}"
            )
            output_path = OUTPUT_DIR / f"{record_id}.txt"
            output_path.write_text(text + "\n", encoding="utf-8")
            rows.append(
                {
                    "record_id": record_id,
                    "politician": occurrence.politician,
                    "state": SPEAKERS[occurrence.politician][0],
                    "date": date,
                    "venue": "Congressional Record speaker remarks",
                    "source_type": "Official Congressional Record PDF",
                    "source_url": f"https://www.govinfo.gov/content/pkg/{package}/pdf/{package}.pdf",
                    "source_page_start": str(page_number + 1),
                    "source_page_end": str(end_page),
                    "page_count": str(end_page - page_number),
                    "transcript_path": str(output_path),
                    "transcript_status": "complete speaker turn; source-preserved",
                    "boundary_status": boundary_status,
                    "text_generated_by_project": "no",
                }
            )

    fieldnames = list(rows[0].keys()) if rows else []
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    multi_page = sum(int(row["page_count"]) > 1 for row in rows)
    print(
        f"Wrote {len(rows)} complete speaker remarks from "
        f"{len(pdfs) - len(skipped)} valid issues; {multi_page} span multiple pages"
    )
    if skipped:
        print("Skipped source files:")
        for item in skipped:
            print(f"- {item}")


if __name__ == "__main__":
    main()
