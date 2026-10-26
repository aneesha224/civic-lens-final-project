"""Civic Lens web server."""
import asyncio
import csv
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .corpus import CorpusStore
from .agents import ResearchDeps, chat_assistant
from .config import MODEL_SETTINGS, configured_model
from .models import ChatRequest, ChatResponse, ResearchRequest
from .public_sources import CACHE_HOURS, discover_public_speeches, import_public_speech as import_transcript
from .topics import TOPIC_TERMS, normalize_topic
from .workflow import run_research

app = FastAPI(title="Civic Lens", version="0.1.0")
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
corpus = CorpusStore()
discovery_tasks: dict[str, asyncio.Task[dict[str, object]]] = {}
discovery_finished_at: dict[str, float] = {}
ROSTER_PATH = Path(__file__).resolve().parents[1] / "data" / "politicians.csv"
PROFILE_PATH = Path(__file__).resolve().parents[1] / "data" / "politician_profiles.json"
def topic_hits(text: str) -> list[dict[str, str]]:
    lowered = text.casefold()
    return [
        {"topic": topic, "matched_term": term}
        for topic, terms in TOPIC_TERMS.items()
        if (term := next((item for item in terms if item in lowered), None))
    ]


def topic_phrase_candidates(text: str, *, per_topic: int = 4, limit: int = 40) -> list[dict[str, str]]:
    """Return short, source-backed wording cues grouped under canonical topics."""
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for topic, terms in TOPIC_TERMS.items():
        found_for_topic = 0
        for term in sorted(terms, key=len, reverse=True):
            if found_for_topic >= per_topic:
                break
            match = re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I)
            if not match:
                continue
            matched_term = match.group(0)
            key = (topic, matched_term.casefold())
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"topic": topic, "phrase": matched_term, "matched_term": matched_term})
            found_for_topic += 1
            if len(candidates) >= limit:
                return candidates
    return candidates

def record_json(record: object) -> dict[str, object]:
    return record.model_dump(mode="json")


def daily_groups(records: list[object]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], list[object]] = {}
    for record in records:
        # Keep distinct publisher transcripts distinct even when they cover the
        # same speech on the same date. Only CR speaker turns are day-grouped.
        source_key = record.record_id if record.source_category == "campaign" else ""
        groups.setdefault(
            (record.politician, str(record.date), record.source_category, source_key),
            [],
        ).append(record)
    output = []
    for group in sorted(
        groups.values(),
        key=lambda items: (items[0].source_category != "campaign", -items[0].date.toordinal()),
    ):
        first = group[0]
        item = record_json(first)
        starts = [record.source_page_start for record in group if record.source_page_start is not None]
        ends = [record.source_page_end for record in group if record.source_page_end is not None]
        item["source_page_start"] = min(starts) if starts else None
        item["source_page_end"] = max(ends) if ends else None
        item["remark_count"] = len(group)
        item["source_label"] = "Campaign / public remarks" if first.source_category == "campaign" else "Congressional Record"
        output.append(item)
    return output

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "records": str(len(corpus.visible_records())),
        "source_records": str(len(corpus.records)),
    }

@app.get("/api/politicians")
def politicians() -> dict[str, object]:
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            names = [row["politician"] for row in csv.DictReader(handle) if row.get("politician")]
    except OSError:
        names = corpus.politicians()
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        by_name = {profile["name"].casefold(): profile for profile in data.get("profiles", [])}
        profiles = [by_name[name.casefold()] for name in names if name.casefold() in by_name]
        as_of = data.get("as_of", "")
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        profiles = []
        as_of = ""
    return {"politicians": names, "profiles": profiles, "as_of": as_of}

@app.get("/api/records")
async def records(politician: str = Query(..., min_length=2), limit: int = Query(1000, ge=1, le=2000)) -> dict[str, object]:
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            roster = {row["politician"].casefold(): row["politician"] for row in csv.DictReader(handle)}
    except OSError:
        roster = {name.casefold(): name for name in corpus.politicians()}
    canonical_name = roster.get(politician.strip().casefold())
    if canonical_name is None:
        raise HTTPException(status_code=404, detail="Choose a politician from the list.")

    key = canonical_name.casefold()
    task = discovery_tasks.get(key)
    now = time.monotonic()
    if task is not None and task.done():
        try:
            completed_result = task.result()
            searched_at = datetime.fromisoformat(str(completed_result["searched_at"]))
            age_hours = (datetime.now(timezone.utc) - searched_at).total_seconds() / 3600
            if age_hours >= CACHE_HOURS:
                task = None
                discovery_tasks.pop(key, None)
                discovery_finished_at.pop(key, None)
        except Exception:
            if now - discovery_finished_at.get(key, now) >= 60:
                task = None
                discovery_tasks.pop(key, None)
                discovery_finished_at.pop(key, None)

    if task is None:
        task = asyncio.create_task(asyncio.to_thread(discover_public_speeches, canonical_name))
        discovery_tasks[key] = task
        task.add_done_callback(lambda _task, name=key: discovery_finished_at.__setitem__(name, time.monotonic()))

    if task.done():
        try:
            discovery = task.result()
            search_status = "ok"
        except Exception:
            logger.exception("On-demand public speech search failed for %s", canonical_name)
            discovery = {"new_transcripts": 0, "leads": [], "cache_status": "search unavailable"}
            search_status = "unavailable"
    else:
        discovery = {"new_transcripts": 0, "leads": [], "cache_status": "loading all mapped election cycles"}
        search_status = "loading"

    # New transcript metadata lives in a flat-file cache and is merged with both
    # existing collections; the Congressional Record remains intact.
    corpus.refresh()
    found_records = corpus.search(canonical_name, limit=100_000)
    found_records.sort(key=lambda item: (item.source_category != "campaign", -item.date.toordinal()))
    all_counts = {
        "congressional_record": sum(item.source_category == "congressional_record" for item in found_records),
        "public_transcripts": sum(item.source_category == "campaign" for item in found_records),
    }
    selected_records = found_records[:limit]
    return {
        "records": daily_groups(selected_records),
        "discovery": discovery,
        "search_status": search_status,
        "source_counts": all_counts,
    }

@app.get("/api/records/{record_id}")
def record_detail(record_id: str) -> dict[str, object]:
    try:
        record = corpus.get(record_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    same_day = [record] if record.source_category == "campaign" else [
        item for item in corpus.records
        if item.politician == record.politician
        and item.date == record.date
        and item.source_category == record.source_category
        and corpus.is_substantive(item)
    ]
    text = corpus.read_day_text(record)
    grouped = record_json(record)
    starts = [item.source_page_start for item in same_day if item.source_page_start is not None]
    ends = [item.source_page_end for item in same_day if item.source_page_end is not None]
    grouped["source_page_start"] = min(starts) if starts else None
    grouped["source_page_end"] = max(ends) if ends else None
    grouped["remark_count"] = len(same_day)
    grouped["transcript_status"] = record.transcript_status
    return {
        "record": grouped,
        "text": text,
        "topic_hints": topic_hits(text),
        "phrase_candidates": topic_phrase_candidates(text),
    }


@app.post("/api/public-speeches/import")
async def import_public_speech(
    politician: str = Query(..., min_length=2),
    source_url: str = Query(..., min_length=8, max_length=2048),
) -> dict[str, object]:
    """Fetch a search lead and make its full transcript readable in Civic Lens."""
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            roster = {row["politician"].casefold(): row["politician"] for row in csv.DictReader(handle)}
    except OSError:
        roster = {name.casefold(): name for name in corpus.politicians()}
    canonical_name = roster.get(politician.strip().casefold())
    if canonical_name is None:
        raise HTTPException(status_code=404, detail="Choose a politician from the list.")
    try:
        metadata = await asyncio.to_thread(import_transcript, canonical_name, source_url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        logger.warning("Could not import a public speech for %s: %s", canonical_name, error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    corpus.refresh()
    try:
        record = corpus.get(str(metadata["record_id"]))
    except ValueError as error:
        raise HTTPException(status_code=500, detail="The transcript was saved but could not be loaded.") from error
    return {"record": record_json(record)}


def _canonical_politician(politician: str) -> str:
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            roster = {row["politician"].casefold(): row["politician"] for row in csv.DictReader(handle)}
    except OSError:
        roster = {name.casefold(): name for name in corpus.politicians()}
    canonical_name = roster.get(politician.strip().casefold())
    if canonical_name is None:
        raise HTTPException(status_code=404, detail="Choose a politician from the list.")
    return canonical_name


@app.get("/api/phrase-trace")
def phrase_trace(
    politician: str = Query(..., min_length=2),
    phrase: str = Query(..., min_length=2, max_length=160),
    source_category: Literal["campaign", "congressional_record", "all"] = "campaign",
) -> dict[str, object]:
    """Return exact phrase occurrences across this politician's in-app speech corpus."""
    canonical_name = _canonical_politician(politician)
    corpus.refresh()
    matches = corpus.search_phrase(canonical_name, phrase, source_category=source_category)
    return {
        "politician": canonical_name,
        "phrase": " ".join(phrase.split()),
        "source_category": source_category,
        "record_count": len(matches),
        "total_occurrences": sum(int(item["occurrence_count"]) for item in matches),
        "records": matches,
    }


@app.get("/api/topic-trace")
def topic_trace(
    politician: str = Query(..., min_length=2),
    topic: str = Query(..., min_length=2, max_length=80),
    source_category: Literal["campaign", "congressional_record", "all"] = "campaign",
) -> dict[str, object]:
    """Find related vocabulary and passages for a policy topic across the corpus."""
    canonical_name = _canonical_politician(politician)
    canonical_topic = normalize_topic(topic)
    if canonical_topic is None:
        choices = ", ".join(TOPIC_TERMS)
        raise HTTPException(status_code=422, detail=f"Choose a policy topic such as {choices}.")
    corpus.refresh()
    matches = corpus.search_topic(
        canonical_name,
        TOPIC_TERMS[canonical_topic],
        source_category=source_category,
    )
    return {
        "politician": canonical_name,
        "topic": canonical_topic,
        "source_category": source_category,
        "record_count": len(matches),
        "total_occurrences": sum(int(item["occurrence_count"]) for item in matches),
        "records": matches,
    }


@app.post("/api/phrase-candidates")
async def phrase_candidates(
    politician: str = Query(..., min_length=2),
    record_id: str = Query(..., min_length=3),
) -> dict[str, object]:
    """Find short transcript wording tied to canonical policy topics."""
    corpus.refresh()
    try:
        record = corpus.get(record_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Choose an available speech.") from error
    if record.politician.casefold() != politician.casefold():
        raise HTTPException(status_code=400, detail="The speech does not belong to this politician.")
    phrases = [
        {
            **item,
            "explanation": f"Search related language about {item['topic']} across this politician’s speeches.",
            "confidence": 1.0,
        }
        for item in topic_phrase_candidates(corpus.read_day_text(record))
    ]
    return {"record_id": record_id, "phrases": phrases, "method": "local topic vocabulary"}

@app.post("/api/analyze")
async def analyze(request: ResearchRequest) -> dict[str, object]:
    try:
        result = await run_research(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Civic Lens analysis failed")
        raise HTTPException(status_code=502, detail="The model service could not complete the analysis. Check the server log for details.") from error
    return result.model_dump(mode="json")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    selected_context = "No remark is selected."
    if request.selected_record_id:
        try:
            record = corpus.get(request.selected_record_id)
            selected_context = (
                f"Selected politician: {record.politician}. "
                f"Selected date: {record.date}. "
                + (
                    f"Selected source pages: {record.source_page_start}-{record.source_page_end}. "
                    if record.source_page_start is not None
                    else "Selected source is a transcript without printed page numbers. "
                )
                + f"Record ID: {record.record_id}."
            )
        except ValueError:
            selected_context = "The selected record could not be found."
    conversation = "\n".join(
        f"{item.role.upper()}: {item.content}" for item in request.history[-20:]
    )
    prompt = (
        "Current page context:\n" + selected_context +
        "\n\nRecent conversation:\n" + (conversation or "(none)") +
        "\n\nUSER QUESTION:\n" + request.message
    )
    try:
        result = await chat_assistant.run(
            prompt,
            deps=ResearchDeps(corpus=corpus),
            model=configured_model(),
            model_settings=MODEL_SETTINGS,
        )
    except Exception as error:
        logger.exception("Civic Lens guide request failed")
        raise HTTPException(
            status_code=502,
            detail="The guide is unavailable. Check the local model credential.",
        ) from error
    return result.output

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
