"""Build a small local test corpus by copying source-preserved records only."""

import csv
import shutil
from pathlib import Path

SOURCE_RECORDS = Path("data/speech_records.csv")
TEST_DIR = Path("data/test")


def main() -> None:
    rows = list(csv.DictReader(SOURCE_RECORDS.open(encoding="utf-8")))
    selected = []
    seen = set()
    for row in rows:
        if row["politician"] in seen:
            continue
        selected.append(row)
        seen.add(row["politician"])
        if len(selected) == 15:
            break

    transcript_dir = TEST_DIR / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    for row in selected:
        source = Path(row["transcript_path"])
        target = transcript_dir / source.name
        shutil.copyfile(source, target)
        row["transcript_path"] = str(target)

    with (TEST_DIR / "speech_records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=selected[0].keys())
        writer.writeheader()
        writer.writerows(selected)
    print(f"Built test corpus with {len(selected)} source-preserved records")


if __name__ == "__main__":
    main()

