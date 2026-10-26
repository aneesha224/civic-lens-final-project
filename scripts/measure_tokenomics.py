"""Run two real Civic Lens workflows and append token-only usage evidence.

Run from any directory with the project's .venv:
    .venv/bin/python scripts/measure_tokenomics.py

The log deliberately stores usage totals and public record identifiers only;
it never stores prompts, transcript text, model outputs, or credentials.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(PROJECT_DIR.parent / ".env")

from app.agents import (  # noqa: E402
    ResearchDeps,
    longitudinal_analyst,
    safety_auditor,
    speech_analyst,
)
from app.config import MODEL_SETTINGS, configured_model  # noqa: E402
from app.corpus import CorpusStore  # noqa: E402
from app.models import ResearchRequest  # noqa: E402


MODEL = os.getenv("AI_MODEL", "gpt-6-luna")
USD_PER_MILLION = {"input": 0.10, "cached_input": 0.01, "output": 0.50}
PRICING_URL = "https://developers.openai.com/api/docs/pricing"
MEASURED_RECORD_ID = "live-speech-ec6efe2bfe39"
MEASURED_TOPIC = "health care"


def usage_row(role: str, result: Any) -> dict[str, int | str]:
    usage = result.usage
    return {
        "agent": role,
        "model_requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "output_tokens": usage.output_tokens,
        "unmeasured_responses": usage.unmeasured_requests,
    }


def summarize(rows: list[dict[str, int | str]]) -> dict[str, int | float]:
    input_tokens = sum(int(row["input_tokens"]) for row in rows)
    cache_read_tokens = sum(int(row["cache_read_tokens"]) for row in rows)
    output_tokens = sum(int(row["output_tokens"]) for row in rows)
    unmeasured_responses = sum(int(row["unmeasured_responses"]) for row in rows)
    uncached_input_tokens = max(0, input_tokens - cache_read_tokens)
    cost_usd = (
        uncached_input_tokens * USD_PER_MILLION["input"]
        + cache_read_tokens * USD_PER_MILLION["cached_input"]
        + output_tokens * USD_PER_MILLION["output"]
    ) / 1_000_000
    return {
        "model_requests": sum(int(row["model_requests"]) for row in rows),
        "input_tokens": input_tokens,
        "uncached_input_tokens": uncached_input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "unmeasured_responses": unmeasured_responses,
        "estimated_openai_list_cost_usd": round(cost_usd, 9),
    }


async def measure(scenario: str, topic: str | None = None) -> dict[str, Any]:
    corpus = CorpusStore()
    selected = corpus.get(MEASURED_RECORD_ID)
    deps = ResearchDeps(corpus=corpus)
    model = configured_model()
    request = ResearchRequest(
        politician=selected.politician,
        record_id=selected.record_id,
        topic=topic,
        analysis_mode="speech" if topic is None else "related_records",
    )
    rows: list[dict[str, int | str]] = []
    started = time.perf_counter()

    speech_prompt = json.dumps({
        "record_id": request.record_id,
        "politician": request.politician,
        "selected_phrase": request.phrase,
        "requested_mode": request.analysis_mode,
    })
    speech_result = await speech_analyst.run(
        speech_prompt, deps=deps, model=model, model_settings=MODEL_SETTINGS
    )
    rows.append(usage_row("speech-analyst", speech_result))

    source_text = corpus.read_day_text(selected)
    verified_evidence = [
        item.model_copy(update={
            "record_id": selected.record_id,
            "politician": selected.politician,
            "date": selected.date,
            "page_start": min((r.source_page_start for r in corpus.records
                if r.politician == selected.politician and r.date == selected.date
                and r.source_category == selected.source_category
                and r.source_page_start is not None), default=None),
            "page_end": max((r.source_page_end for r in corpus.records
                if r.politician == selected.politician and r.date == selected.date
                and r.source_category == selected.source_category
                and r.source_page_end is not None), default=None),
            "source_url": selected.source_url,
        })
        for item in speech_result.output.evidence
        if item.quote in source_text
    ]
    removed_quotes = len(speech_result.output.evidence) - len(verified_evidence)
    caveats = list(speech_result.output.caveats)
    if removed_quotes:
        caveats.append(
            f"{removed_quotes} proposed excerpt(s) were removed because they did not match the selected source text exactly."
        )
    speech_analysis = speech_result.output.model_copy(update={
        "evidence": verified_evidence,
        "caveats": caveats,
    })

    longitudinal_analysis = None
    if topic:
        longitudinal_prompt = json.dumps({
            "politician": request.politician,
            "topic": topic,
            "phrase": request.phrase,
            "selected_record": speech_analysis.model_dump(mode="json"),
        })
        longitudinal_result = await longitudinal_analyst.run(
            longitudinal_prompt,
            deps=deps,
            model=model,
            model_settings=MODEL_SETTINGS,
        )
        rows.append(usage_row("longitudinal-analyst", longitudinal_result))
        longitudinal_analysis = longitudinal_result.output

    safety_prompt = json.dumps({
        "request": request.model_dump(mode="json"),
        "speech_analysis": speech_analysis.model_dump(mode="json"),
        "longitudinal_analysis": (
            longitudinal_analysis.model_dump(mode="json") if longitudinal_analysis else None
        ),
    })
    safety_result = await safety_auditor.run(
        safety_prompt, deps=deps, model=model, model_settings=MODEL_SETTINGS
    )
    rows.append(usage_row("safety-auditor", safety_result))

    return {
        "scenario": scenario,
        "record_id": selected.record_id,
        "date": selected.date.isoformat(),
        "topic_requested": topic is not None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "agents": rows,
        "totals": summarize(rows),
    }


async def main() -> None:
    if not (os.getenv("PORTKEY_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise SystemExit("No PORTKEY_API_KEY or OPENAI_API_KEY is configured; no request was sent.")
    if MODEL != "gpt-6-luna":
        raise SystemExit(
            "This measurement uses gpt-6-luna rates; set AI_MODEL=gpt-6-luna before running."
        )

    results = [
        await measure("speech-only"),
        await measure("topic-comparison", MEASURED_TOPIC),
    ]
    entry = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL,
        "pricing_basis": {
            "source": PRICING_URL,
            "usd_per_million_tokens": USD_PER_MILLION,
            "cost_note": "OpenAI list-price estimate; excludes any separate gateway markup or tax.",
        },
        "runs": results,
    }

    evidence_path = PROJECT_DIR / "evidence" / "tokenomics_runs.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    previous = []
    if evidence_path.exists():
        previous = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(previous, list):
            raise SystemExit("Existing evidence file is not a run list; refusing to overwrite it.")
    previous.append(entry)
    evidence_path.write_text(json.dumps(previous, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(entry, indent=2))
    print(f"Evidence saved to {evidence_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    asyncio.run(main())
