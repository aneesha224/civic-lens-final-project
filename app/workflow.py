"""Programmatic coordinator for the PydanticAI agent team."""

from __future__ import annotations

import json

from dotenv import load_dotenv

from .agents import ResearchDeps, longitudinal_analyst, safety_auditor, speech_analyst
from .config import MODEL_SETTINGS, configured_model
from .corpus import CorpusStore
from .models import CivicLensResult, LongitudinalAnalysis, ResearchRequest, SafetyReview
from .topics import TOPIC_TERMS, normalize_topic

load_dotenv()


async def run_research(request: ResearchRequest) -> CivicLensResult:
    """Run the specialist team for one selected remark and optional topic."""
    corpus = CorpusStore()
    selected = corpus.get(request.record_id)
    if selected.politician.casefold() != request.politician.casefold():
        raise ValueError("The selected record does not belong to the requested politician.")
    deps = ResearchDeps(corpus=corpus)
    model = configured_model()

    speech_prompt = json.dumps(
        {
            "record_id": request.record_id,
            "politician": request.politician,
            "selected_phrase": request.phrase,
            "topic": request.topic,
            "requested_mode": request.analysis_mode,
        }
    )
    speech_result = await speech_analyst.run(
        speech_prompt, deps=deps, model=model, model_settings=MODEL_SETTINGS
    )
    speech_analysis = speech_result.output
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
            "venue": selected.venue,
            "source_category": selected.source_category,
        })
        for item in speech_analysis.evidence
        if item.quote in source_text
    ]
    removed_quotes = len(speech_analysis.evidence) - len(verified_evidence)
    caveats = list(speech_analysis.caveats)
    if removed_quotes:
        caveats.append(
            f"{removed_quotes} proposed excerpt(s) were removed because they did not match the selected source text exactly."
        )
    speech_analysis = speech_analysis.model_copy(update={
        "evidence": verified_evidence,
        "caveats": caveats,
    })

    longitudinal: LongitudinalAnalysis | None = None
    if request.topic or request.phrase:
        topic = request.topic or request.phrase or "selected phrase"
        canonical_topic = normalize_topic(topic)
        terms = TOPIC_TERMS.get(canonical_topic or "", [topic])
        date_is_established = "retrieval date used" not in selected.transcript_status.casefold()
        earlier_statements = (
            corpus.search_earlier_topic_citations(
                request.politician,
                terms,
                before_date=selected.date,
                selected_record_id=selected.record_id,
                source_category=request.source_category,
            )
            if date_is_established else []
        )
        longitudinal_prompt = json.dumps(
            {
                "politician": request.politician,
                "topic": topic,
                "phrase": request.phrase,
                "selected_date": selected.date.isoformat(),
                "selected_date_is_established": date_is_established,
                "source_category": request.source_category,
                "earlier_statements": [
                    {
                        "record_id": item.record_id,
                        "date": item.date.isoformat(),
                        "venue": item.venue,
                        "source_category": item.source_category,
                        "quote": item.quote,
                        "source_url": str(item.source_url),
                    }
                    for item in earlier_statements
                ],
                "selected_record": speech_analysis.model_dump(mode="json"),
            }
        )
        longitudinal_result = await longitudinal_analyst.run(
            longitudinal_prompt,
            deps=deps,
            model=model,
            model_settings=MODEL_SETTINGS,
        )
        longitudinal_output = longitudinal_result.output
        longitudinal = longitudinal_output.model_copy(update={
            "earlier_statements": earlier_statements,
            "timeline": [],
            "record_count": len(earlier_statements),
            "comparison_points": longitudinal_output.comparison_points if earlier_statements else [],
            "earliest_observed_date": min((item.date for item in earlier_statements), default=None),
            "latest_observed_date": max((item.date for item in earlier_statements), default=None),
            "limitations": longitudinal_output.limitations + ([
                "The source does not establish the selected speech date, so earlier statements cannot be ordered reliably."
            ] if not date_is_established else []),
            "synthesis": longitudinal_output.synthesis if earlier_statements else (
                "The source does not establish when this speech happened, so Civic Lens cannot reliably identify what the speaker said before it."
                if not date_is_established else
                "No earlier matching statements were found in the selected source set, "
                "so there is not enough evidence here to compare the speaker’s wording."
            ),
        })

    safety_prompt = json.dumps(
        {
            "request": request.model_dump(mode="json"),
            "speech_analysis": speech_analysis.model_dump(mode="json"),
            "longitudinal_analysis": (
                longitudinal.model_dump(mode="json") if longitudinal else None
            ),
        }
    )
    safety_result = await safety_auditor.run(
        safety_prompt, deps=deps, model=model, model_settings=MODEL_SETTINGS
    )
    safety: SafetyReview = safety_result.output
    return CivicLensResult(
        request=request,
        selected_record=selected,
        speech_analysis=speech_analysis,
        longitudinal_analysis=longitudinal,
        safety_review=safety,
    )
