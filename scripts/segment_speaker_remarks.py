"""Create exact speaker-level excerpts from source-preserved page transcripts.

This script only copies substrings from the existing PDF extraction. It does
not correct, summarize, rewrite, or generate any speech text.
"""

import csv
import re
from pathlib import Path

RECORDS_PATH = Path("data/speech_records.csv")
OUTPUT_DIR = Path("data/segmented_transcripts")

SPEAKER_HEADINGS = {
    "Kevin McCarthy": r"Mr\. (?:KEVIN )?MCCARTHY\.",
    "John Cornyn": r"Mr\. (?:JOHN )?CORNYN\.",
    "Ted Cruz": r"Mr\. (?:TED )?CRUZ\.",
    "Marco Rubio": r"Mr\. (?:MARCO )?RUBIO\.",
    "Rick Scott": r"Mr\. (?:RICK )?SCOTT(?: of Florida)?\.",
    "Kirsten Gillibrand": r"(?:Ms|Mrs)\. (?:KIRSTEN )?GILLIBRAND\.",
    "Hakeem Jeffries": r"Mr\. (?:HAKEEM )?JEFFRIES\.",
    "Pat Toomey": r"Mr\. (?:PAT )?TOOMEY\.",
    "Mike Kelly": r"Mr\. (?:MIKE )?KELLY(?: of Pennsylvania)?\.",
    "Tammy Duckworth": r"Ms\. (?:TAMMY )?DUCKWORTH\.",
    "David Scott": r"Mr\. (?:DAVID )?SCOTT of Georgia\.",
    "Hank Johnson": r"Mr\. (?:HANK )?JOHNSON of Georgia\.",
    "Thom Tillis": r"Mr\. (?:THOM )?TILLIS\.",
    "Virginia Foxx": r"(?:Ms|Mrs)\. (?:VIRGINIA )?FOXX\.",
    "Gary Peters": r"Mr\. (?:GARY )?PETERS\.",
    "Justin Amash": r"Mr\. (?:JUSTIN )?AMASH\.",
}

# Congressional Record speaker labels usually start at the beginning of a line.
NEXT_SPEAKER = re.compile(
    r"(?m)^(?:Mr\.|Ms\.|Mrs\.|Miss\.)\s+[A-Z][A-Z .'-]*(?:\s+of\s+[A-Z][A-Za-z'-]+)?\."
)


def extract_segment(text: str, politician: str) -> tuple[str, int, int] | None:
    heading = re.compile(r"(?m)^" + SPEAKER_HEADINGS[politician])
    start_match = heading.search(text)
    if not start_match:
        return None

    start = start_match.start()
    next_match = NEXT_SPEAKER.search(text, start_match.end())
    end = next_match.start() if next_match else len(text)
    segment = text[start:end].strip()
    return segment, start, end


def main() -> None:
    rows = list(csv.DictReader(RECORDS_PATH.open(encoding="utf-8")))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        source_text = Path(row["transcript_path"]).read_text(encoding="utf-8")
        result = extract_segment(source_text, row["politician"])
        row["segment_status"] = "unsegmented"
        row["segment_start_char"] = ""
        row["segment_end_char"] = ""
        row["segmented_transcript_path"] = ""
        if result:
            segment, start, end = result
            output_path = OUTPUT_DIR / f"{row['record_id']}.txt"
            output_path.write_text(segment + "\n", encoding="utf-8")
            row["segment_status"] = "exact source substring"
            row["segment_start_char"] = str(start)
            row["segment_end_char"] = str(end)
            row["segmented_transcript_path"] = str(output_path)

    with RECORDS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    segmented = sum(row["segment_status"] == "exact source substring" for row in rows)
    print(f"Segmented {segmented} of {len(rows)} records as exact source substrings")


if __name__ == "__main__":
    main()

