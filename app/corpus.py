"""Local, read-only tools for the reconstructed Congressional Record corpus."""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path

from .models import Citation, SpeechRecord


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORDS_PATH = PROJECT_ROOT / "data" / "complete_speech_records.csv"
CAMPAIGN_RECORDS_PATH = PROJECT_ROOT / "data" / "campaign_speech_records.csv"
LIVE_RECORDS_PATH = PROJECT_ROOT / "data" / "campaign_speeches" / "live_cache" / "records"
PROCEDURAL_MARKERS = (
    "parliamentary inquiry",
    "the speaker pro tempore",
    "the presiding officer",
    "ask unanimous consent",
    "i yield the floor",
    "motion to adjourn",
    "the clerk will call",
)


class CorpusStore:
    """Read-only access to metadata and exact source-preserved remarks."""

    def __init__(self, records_path: Path = RECORDS_PATH) -> None:
        self.records_path = records_path
        self.project_root = records_path.parent.parent
        self.records: list[SpeechRecord] = []
        self.refresh()

    def refresh(self) -> None:
        """Reload local collections, including transcripts fetched on demand."""
        records: list[SpeechRecord] = []
        campaign_path = self.project_root / "data" / "campaign_speech_records.csv"
        live_records_path = self.project_root / "data" / "campaign_speeches" / "live_cache" / "records"
        for path, category in (
            (self.records_path, "congressional_record"),
            (campaign_path, "campaign"),
        ):
            if not path.is_file():
                continue
            with path.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    row["source_category"] = row.get("source_category") or category
                    for field in ("source_page_start", "source_page_end", "page_count"):
                        if row.get(field) == "":
                            row[field] = None
                    records.append(SpeechRecord.model_validate(row))
        if live_records_path.is_dir():
            for path in sorted(live_records_path.glob("*.json")):
                try:
                    row = json.loads(path.read_text(encoding="utf-8"))
                    # Earlier experimental cache versions could capture a search
                    # result page or article excerpt. Only surface records that
                    # passed the current transcript-title and length checks.
                    if not row.get("transcript_status", "").startswith("on-demand v5 transcript;"):
                        continue
                    records.append(SpeechRecord.model_validate(row))
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
        self.records = records
        self._by_id = {record.record_id: record for record in records}

    def politicians(self) -> list[str]:
        return sorted({record.politician for record in self.visible_records()})

    def is_substantive(self, record: SpeechRecord) -> bool:
        """Hide short procedural exchanges while retaining them on disk."""
        text = self.read_text(record)
        words = len(text.split())
        lowered = " ".join(text.casefold().split())
        if words < 35:
            return False
        if record.source_category == "congressional_record" and words < 180 and any(marker in lowered for marker in PROCEDURAL_MARKERS):
            return False
        return True

    def visible_records(self) -> list[SpeechRecord]:
        return [record for record in self.records if self.is_substantive(record)]

    def search(
        self,
        politician: str,
        *,
        topic_terms: list[str] | None = None,
        limit: int = 20,
    ) -> list[SpeechRecord]:
        normalized = politician.casefold()
        matches = [
            record
            for record in self.records
            if record.politician.casefold() == normalized and self.is_substantive(record)
        ]
        if topic_terms:
            terms = [term.casefold() for term in topic_terms if term.strip()]
            matches = [
                record
                for record in matches
                if any(term in self.read_text(record).casefold() for term in terms)
            ]
        return sorted(matches, key=lambda record: record.date)[:limit]

    def search_phrase(
        self,
        politician: str,
        phrase: str,
        *,
        source_category: str = "campaign",
        excerpts_per_record: int = 5,
    ) -> list[dict[str, object]]:
        """Find literal, case-insensitive phrase uses in each available speech."""
        normalized_name = politician.casefold()
        needle = " ".join(phrase.split())
        pattern = re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", re.IGNORECASE)
        source_matches: list[dict[str, object]] = []
        for record in self.records:
            if record.politician.casefold() != normalized_name or not self.is_substantive(record):
                continue
            if source_category != "all" and record.source_category != source_category:
                continue
            text = " ".join(self.read_text(record).split())
            hits = list(pattern.finditer(text))
            if not hits:
                continue
            excerpts = []
            for hit in hits[:excerpts_per_record]:
                start = max(0, hit.start() - 130)
                end = min(len(text), hit.end() + 170)
                excerpts.append(text[start:end])
            tokens = re.findall(r"[^\W_]+", text.casefold())
            shingles = {tuple(tokens[index:index + 5]) for index in range(max(1, len(tokens) - 4))}
            source_matches.append({
                "record": record.model_dump(mode="json"),
                "occurrence_count": len(hits),
                "excerpts": excerpts,
                "_shingles": shingles,
            })

        # Several publishers can carry the same speech. Treat highly similar
        # campaign transcripts as one speech event and retain all citations.
        clusters: list[dict[str, object]] = []
        for match in source_matches:
            record = match["record"]
            cluster = None
            if record["source_category"] == "campaign":
                for prior in clusters:
                    if prior["record"]["source_category"] != "campaign":
                        continue
                    left, right = match["_shingles"], prior["_shingles"]
                    union = left | right
                    similarity = len(left & right) / len(union) if union else 1.0
                    if similarity >= 0.60:
                        cluster = prior
                        break
            source = {
                key: record[key]
                for key in ("record_id", "date", "venue", "source_url", "source_type", "transcript_status")
            }
            if cluster is None:
                cluster = {
                    **match,
                    "sources": [source],
                    "_preference": int("on-demand" not in record["transcript_status"].casefold()),
                }
                clusters.append(cluster)
                continue
            cluster["sources"].append(source)
            preference = int("on-demand" not in record["transcript_status"].casefold())
            if preference > cluster["_preference"]:
                for key in ("record", "excerpts", "_shingles", "occurrence_count"):
                    cluster[key] = match[key]
                cluster["_preference"] = preference

        for cluster in clusters:
            cluster.pop("_shingles", None)
            cluster.pop("_preference", None)
        return sorted(clusters, key=lambda item: item["record"]["date"])

    def search_topic(
        self,
        politician: str,
        terms: list[str],
        *,
        source_category: str = "campaign",
        excerpts_per_record: int = 3,
    ) -> list[dict[str, object]]:
        """Find speech passages using related vocabulary for a topic, not one exact phrase."""
        normalized_name = politician.casefold()
        alternatives = "|".join(re.escape(term.strip()) for term in sorted(terms, key=len, reverse=True) if term.strip())
        if not alternatives:
            return []
        pattern = re.compile(r"(?<!\w)(?:" + alternatives + r")(?!\w)", re.IGNORECASE)
        matches: list[dict[str, object]] = []
        for record in self.records:
            if record.politician.casefold() != normalized_name or not self.is_substantive(record):
                continue
            if source_category != "all" and record.source_category != source_category:
                continue
            text = " ".join(self.format_for_reading(self.read_text(record)).split())
            hits = list(pattern.finditer(text))
            if not hits:
                continue
            excerpts = []
            last_end = -1
            for hit in hits:
                start = max(0, hit.start() - 190)
                end = min(len(text), hit.end() + 230)
                if start < last_end:
                    continue
                excerpts.append(text[start:end])
                last_end = end
                if len(excerpts) >= excerpts_per_record:
                    break
            tokens = re.findall(r"[^\W_]+", text.casefold())
            shingles = {tuple(tokens[index:index + 5]) for index in range(max(1, len(tokens) - 4))}
            matched_terms = sorted({hit.group(0).casefold() for hit in hits})
            matches.append({
                "record": record.model_dump(mode="json"),
                "occurrence_count": len(hits),
                "matched_terms": matched_terms,
                "excerpts": excerpts,
                "_shingles": shingles,
                "_preference": int("on-demand" not in record.transcript_status.casefold()),
            })

        clusters: list[dict[str, object]] = []
        for match in matches:
            record = match["record"]
            cluster = None
            if record["source_category"] == "campaign":
                for prior in clusters:
                    if prior["record"]["source_category"] != "campaign":
                        continue
                    left, right = match["_shingles"], prior["_shingles"]
                    union = left | right
                    similarity = len(left & right) / len(union) if union else 1.0
                    if similarity >= 0.60:
                        cluster = prior
                        break
            source = {
                key: record[key]
                for key in ("record_id", "date", "venue", "source_url", "source_type", "transcript_status")
            }
            if cluster is None:
                clusters.append({**match, "sources": [source]})
                continue
            cluster["sources"].append(source)
            cluster["occurrence_count"] = max(cluster["occurrence_count"], match["occurrence_count"])
            cluster["matched_terms"] = sorted(set(cluster["matched_terms"]) | set(match["matched_terms"]))
            if match["_preference"] > cluster["_preference"]:
                for key in ("record", "excerpts", "_shingles", "_preference"):
                    cluster[key] = match[key]

        for cluster in clusters:
            cluster.pop("_shingles", None)
            cluster.pop("_preference", None)
        return sorted(clusters, key=lambda item: item["record"]["date"])

    def search_earlier_topic_citations(
        self,
        politician: str,
        terms: list[str],
        *,
        before_date: date,
        selected_record_id: str,
        source_category: str = "all",
        limit: int = 6,
    ) -> list[Citation]:
        """Return exact topic passages from distinct statements before a selected date."""
        clean_terms = [term.strip() for term in terms if term.strip()]
        if not clean_terms:
            return []
        alternatives = "|".join(re.escape(term) for term in sorted(clean_terms, key=len, reverse=True))
        pattern = re.compile(r"(?<!\w)(?:" + alternatives + r")(?!\w)", re.IGNORECASE)
        candidates = sorted(
            (
                record for record in self.records
                if record.politician.casefold() == politician.casefold()
                and record.record_id != selected_record_id
                and record.date < before_date
                and (source_category == "all" or record.source_category == source_category)
            ),
            key=lambda record: (record.date, record.record_id),
            reverse=True,
        )
        citations: list[Citation] = []
        seen_source_texts: set[str] = set()
        for record in candidates:
            if not self.is_substantive(record):
                continue
            text = self.format_for_reading(self.read_text(record))
            paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
            ranked = []
            for index, paragraph in enumerate(paragraphs):
                hits = list(pattern.finditer(paragraph))
                if hits:
                    ranked.append((len(hits), -index, paragraph, hits[0]))
            if not ranked:
                continue
            _, _, paragraph, hit = max(ranked, key=lambda item: (item[0], item[1]))
            start = max(0, hit.start() - 180)
            end = min(len(paragraph), hit.end() + 360)
            if start:
                start = paragraph.find(" ", start)
                start = 0 if start < 0 else start + 1
            if end < len(paragraph):
                boundary = paragraph.find(" ", end)
                if boundary >= 0:
                    end = boundary
            quote = paragraph[start:end].strip()
            signature = " ".join(text.casefold().split())
            if signature in seen_source_texts:
                continue
            seen_source_texts.add(signature)
            citations.append(self.citation(record, quote))
            if len(citations) >= limit:
                break
        return citations

    def get(self, record_id: str) -> SpeechRecord:
        try:
            return self._by_id[record_id]
        except KeyError as error:
            raise ValueError(f"Unknown corpus record: {record_id}") from error

    def read_text(self, record: SpeechRecord) -> str:
        if record.source_category == "campaign":
            path = self.project_root / "data" / "campaign_speeches" / record.transcript_path
        else:
            path = self.project_root / record.transcript_path
        if not path.is_file():
            raise FileNotFoundError(f"Missing transcript for {record.record_id}: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def format_for_reading(text: str) -> str:
        """Join PDF line wraps while preserving paragraph breaks and wording."""
        paragraphs = []
        for block in re.split(r"\n\s*\n+", text.strip()):
            lines = [" ".join(line.split()) for line in block.splitlines() if line.strip()]
            paragraph = " ".join(lines)
            paragraph = re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "", paragraph)
            if paragraph:
                paragraphs.append(paragraph)
        return "\n\n".join(paragraphs)

    def read_day_text(self, record: SpeechRecord) -> str:
        """Read all same-day turns as clean paragraphs for the selected source."""
        if record.source_category == "campaign":
            return self.format_for_reading(self.read_text(record))
        same_day = [
            item for item in self.records
            if item.politician == record.politician
            and item.date == record.date
            and item.source_category == record.source_category
            and self.is_substantive(item)
        ]
        same_day.sort(key=lambda item: (
            item.source_page_start is None,
            item.source_page_start or 0,
            item.record_id,
        ))
        text = "\n\n".join(self.read_text(item) for item in same_day)
        return self.format_for_reading(text)

    def citation(self, record: SpeechRecord, quote: str) -> Citation:
        return Citation(
            record_id=record.record_id,
            politician=record.politician,
            date=record.date,
            page_start=record.source_page_start,
            page_end=record.source_page_end,
            quote=quote,
            source_url=record.source_url,
            venue=record.venue,
            source_category=record.source_category,
        )
