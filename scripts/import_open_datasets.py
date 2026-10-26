"""Add roster speeches from two open datasets to the public-source manifest.

Sources (downloaded at run time, never edited):
  1. OpenML #43709 "US-2020-Presidential-Election-Speeches" (GPL-2), Rev.com
     transcripts of 2020-cycle speeches, interviews, and town halls.
     https://www.openml.org/d/43709
  2. leops95/sots "U.S. State of the State transcripts" (CC0-1.0), 1995-2022.
     https://github.com/leops95/sots

Only roster politicians are kept. Debates are skipped. In multi-speaker
transcripts only the politician's own time-stamped turns are kept. Texts that
duplicate an existing record (>= 60% 5-word-shingle overlap) are skipped.

Run from the Final Project folder:
    .venv/bin/python scripts/import_open_datasets.py
    .venv/bin/python scripts/import_campaign_speeches.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import ssl
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "data" / "campaign_speeches"
MANIFEST = CAMPAIGN / "manifest.csv"
CAPTURES = CAMPAIGN / "captures" / "open_datasets"
ROSTER = ROOT / "data" / "politicians.csv"

OPENML_ARFF = "https://openml.org/data/v1/download/22102534/US-2020-Presidential-Election-Speeches.arff"
OPENML_PAGE = "https://www.openml.org/d/43709"
SOTS_META = "https://raw.githubusercontent.com/leops95/sots/master/metadata.csv"
SOTS_RAW = "https://raw.githubusercontent.com/leops95/sots/master/speeches_raw/"
SOTS_PAGE = "https://github.com/leops95/sots"

MIN_WORDS = 300
TURN = re.compile(r"(?m)^\s*([A-Z][A-Za-z.'\- ]{1,60}?)\s*:?\s*\((\d{1,2}:\d{2}(?::\d{2})?)\)\s*:?")


def fetch(url: str) -> bytes:
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": "CivicLens-dataset-import/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
        return resp.read()


def shingles(text: str) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[^\W_]+", text.casefold())
    return {tuple(tokens[i:i + 5]) for i in range(max(1, len(tokens) - 4))}


def is_duplicate(text: str, existing: list[set]) -> bool:
    new = shingles(text)
    for old in existing:
        union = new | old
        if union and len(new & old) / len(union) >= 0.60:
            return True
        # also catch a new text that is a subset/superset of an existing one
        smaller = min(len(new), len(old)) or 1
        if len(new & old) / smaller >= 0.80:
            return True
    return False


def speaker_turns(text: str, politician: str) -> tuple[str, bool]:
    """Keep only the politician's turns when the transcript has timestamped speakers."""
    heads = list(TURN.finditer(text))
    if len(heads) < 2:
        return text.strip(), False
    surname = politician.split()[-1].casefold()
    parts = []
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        if surname in head.group(1).casefold():
            parts.append(text[head.end():end].strip())
    return "\n\n".join(p for p in parts if p), True


def parse_arff(raw: str) -> list[dict[str, str]]:
    names, data_lines, in_data = [], [], False
    for line in raw.splitlines():
        if not in_data:
            low = line.strip().lower()
            if low.startswith("@attribute"):
                m = re.match(r"@attribute\s+('([^']+)'|\"([^\"]+)\"|(\S+))", line.strip(), re.I)
                names.append(m.group(2) or m.group(3) or m.group(4))
            elif low.startswith("@data"):
                in_data = True
        elif line.strip() and not line.startswith("%"):
            data_lines.append(line)
    rows = []
    escapes = {"n": "\n", "r": "", "t": " ", "'": "'", '"': '"', "\\": "\\"}
    for line in data_lines:
        values, buf, quote, i = [], [], None, 0
        while i < len(line):
            ch = line[i]
            if quote:
                if ch == "\\" and i + 1 < len(line):
                    buf.append(escapes.get(line[i + 1], line[i + 1]))
                    i += 2
                    continue
                if ch == quote:
                    quote = None
                else:
                    buf.append(ch)
            elif ch in "'\"":
                quote = ch
            elif ch == ",":
                values.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
            i += 1
        values.append("".join(buf).strip())
        if len(values) != len(names):
            continue
        rows.append({k: ("" if v == "?" else v) for k, v in zip(names, values)})
    return rows


def main() -> None:
    with ROSTER.open(encoding="utf-8", newline="") as h:
        roster = {r["politician"]: r["state"] for r in csv.DictReader(h)}
    with MANIFEST.open(encoding="utf-8", newline="") as h:
        reader = csv.DictReader(h)
        fields = reader.fieldnames
        manifest = list(reader)
    existing: dict[str, list[set]] = {}
    for row in manifest:
        path = CAMPAIGN / row["transcript_path"]
        if path.is_file():
            existing.setdefault(row["politician"], []).append(shingles(path.read_text(encoding="utf-8")))
    known_ids = {row["record_id"] for row in manifest}
    CAPTURES.mkdir(parents=True, exist_ok=True)
    added: list[dict[str, str]] = []
    skipped = {"duplicate": 0, "short": 0, "debate": 0}

    def add(politician, date, venue, source_type, url, text, status, boundary, key):
        words = len(text.split())
        if words < MIN_WORDS:
            skipped["short"] += 1
            return
        if is_duplicate(text, existing.get(politician, [])):
            skipped["duplicate"] += 1
            return
        slug = re.sub(r"[^a-z0-9]+", "-", politician.casefold()).strip("-")
        record_id = f"{slug}-open-{hashlib.sha1(key.encode()).hexdigest()[:10]}"
        if record_id in known_ids:
            return
        rel = f"captures/open_datasets/{record_id}.txt"
        (CAMPAIGN / rel).write_text(text.strip() + "\n", encoding="utf-8")
        row = {f: "" for f in fields}
        row.update({
            "record_id": record_id, "politician": politician, "state": roster[politician],
            "date": date, "venue": venue[:200], "source_type": source_type, "source_url": url,
            "transcript_path": rel, "transcript_status": status, "boundary_status": boundary,
        })
        added.append(row)
        known_ids.add(record_id)
        existing.setdefault(politician, []).append(shingles(text))

    # 1. OpenML 2020 election speeches
    print("Downloading OpenML 2020 election speeches ...")
    rows = parse_arff(fetch(OPENML_ARFF).decode("utf-8", errors="replace"))
    print(f"  {len(rows)} rows parsed")
    for row in rows:
        speaker = (row.get("speaker") or "").strip()
        politician = next((p for p in roster if p.casefold() == speaker.casefold()), None)
        if not politician:
            continue
        kind = (row.get("type") or "").strip()
        if "debate" in kind.casefold() or "debate" in (row.get("title") or "").casefold():
            skipped["debate"] += 1
            continue
        text, multi = speaker_turns(row.get("text") or "", politician)
        title = (row.get("title") or f"{kind} by {politician}").strip()
        location = (row.get("location") or "").strip()
        add(
            politician, "2020-10-21",
            f"{title}" + (f" — {location}" if location else ""),
            f"OpenML 43709 open dataset (Rev.com transcript; {kind or 'type not recorded'})",
            OPENML_PAGE, text,
            "complete source transcript from open dataset; retrieval date used because speech date is unknown (2019-2020 election cycle; dataset collected 2020-10-21)",
            "speaker turns isolated from timestamped transcript" if multi else "single speaker transcript block from dataset",
            f"openml|{title}|{len(text)}",
        )

    # 2. State of the State addresses (governors) for roster members
    print("Downloading State of the State metadata ...")
    meta = list(csv.DictReader(io.StringIO(fetch(SOTS_META).decode("utf-8", errors="replace"))))
    surname_first = {"_".join(reversed(p.split(maxsplit=1))).casefold(): p for p in roster}
    for row in meta:
        politician = surname_first.get((row.get("speaker") or "").casefold())
        if not politician:
            continue
        print(f"  fetching {row['filename']}")
        try:
            text = fetch(SOTS_RAW + row["filename"]).decode("utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001
            print(f"  could not fetch {row['filename']}: {error}")
            continue
        kind = {"sots": "State of the State address", "budg": "Budget address", "inaug": "Inaugural address"}.get(row.get("type", ""), "Governor's address")
        add(
            politician, f"{row['year']}-01-01",
            f"{row['year']} {row.get('st_name', '')} {kind}",
            f"leops95/sots open dataset (CC0); original source {row.get('source', '')}".strip(),
            row.get("source") or SOTS_PAGE, text,
            f"complete source transcript from open dataset ({row.get('quality', 'quality not recorded')}); delivery year from dataset, month/day not recorded",
            "single speaker address",
            f"sots|{row['filename']}",
        )

    if added:
        with MANIFEST.open("a", encoding="utf-8", newline="") as h:
            csv.DictWriter(h, fieldnames=fields).writerows(added)
    by_person: dict[str, int] = {}
    for row in added:
        by_person[row["politician"]] = by_person.get(row["politician"], 0) + 1
    print(f"\nAdded {len(added)} records: {by_person}")
    print(f"Skipped: {skipped}")
    print("Now run: .venv/bin/python scripts/import_campaign_speeches.py")


if __name__ == "__main__":
    main()
