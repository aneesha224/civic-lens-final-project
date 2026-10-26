"""Run Civic Lens's live public-source search for every politician under 30 speeches.

Uses the app's own discovery code (Bing + Google News RSS -> transcript pages ->
extracted text in data/campaign_speeches/live_cache/). Retrieved texts are
labeled for boundary review; nothing is generated.

Run from the Final Project folder:  python scripts/fill_gaps.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.corpus import CorpusStore  # noqa: E402
from app.public_sources import discover_public_speeches  # noqa: E402

TARGET = 30


def counts() -> dict[str, int]:
    store = CorpusStore()
    out: dict[str, int] = {}
    for record in store.records:
        if record.source_category == "campaign" and store.is_substantive(record):
            out[record.politician] = out.get(record.politician, 0) + 1
    return out


def main() -> None:
    with (ROOT / "data" / "politicians.csv").open(encoding="utf-8", newline="") as h:
        roster = [r["politician"] for r in csv.DictReader(h)]
    before = counts()
    gaps = sorted((p for p in roster if before.get(p, 0) < TARGET), key=lambda p: before.get(p, 0))
    print(f"Searching for {len(gaps)} politicians under {TARGET}: {', '.join(gaps)}\n")
    for name in gaps:
        print(f"- {name}: searching ...", flush=True)
        try:
            result = discover_public_speeches(name, force=True)
            print(f"  {result.get('new_transcripts', 0)} new transcripts, {len(result.get('leads', []))} leads checked")
        except Exception as error:  # noqa: BLE001
            print(f"  search failed: {error}")
    after = counts()
    print("\nPolitician            before  after")
    for name in roster:
        print(f"{name:<22}{before.get(name, 0):>6}{after.get(name, 0):>7}")


if __name__ == "__main__":
    main()
