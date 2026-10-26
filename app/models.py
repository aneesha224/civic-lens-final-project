"""Typed inputs and outputs shared by the Civic Lens agent team."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SpeechRecord(BaseModel):
    record_id: str
    politician: str
    state: str
    date: date
    venue: str
    source_type: str = "Official source"
    source_category: Literal["congressional_record", "campaign"] = "congressional_record"
    source_url: HttpUrl
    source_page_start: int | None = None
    source_page_end: int | None = None
    page_count: int | None = None
    transcript_path: str
    transcript_status: str
    boundary_status: str


class Citation(BaseModel):
    record_id: str
    politician: str
    date: date
    page_start: int | None = None
    page_end: int | None = None
    quote: str = Field(min_length=1)
    source_url: HttpUrl
    venue: str = ""
    source_category: Literal["congressional_record", "campaign"] = "congressional_record"


class PhraseCandidate(BaseModel):
    phrase: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    explanation: str
    evidence: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class SpeechAnalysis(BaseModel):
    record_id: str
    summary: str
    claims: list[str] = Field(default_factory=list)
    phrases: list[PhraseCandidate] = Field(default_factory=list)
    evidence: list[Citation] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    date: date
    record_id: str
    language: str
    interpretation: str
    evidence: list[Citation] = Field(default_factory=list)


class LongitudinalAnalysis(BaseModel):
    politician: str
    topic: str
    corpus_scope: str
    earliest_observed_date: date | None = None
    latest_observed_date: date | None = None
    record_count: int = Field(ge=0)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    earlier_statements: list[Citation] = Field(default_factory=list)
    synthesis: str
    comparison_points: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SafetyReview(BaseModel):
    approved: bool
    concerns: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)
    evidence_complete: bool
    scope_warning: str


class ResearchRequest(BaseModel):
    politician: str
    record_id: str
    topic: str | None = None
    phrase: str | None = None
    source_category: Literal["campaign", "congressional_record", "all"] = "all"
    analysis_mode: Literal[
        "speech",
        "related_records",
        "language_change",
        "first_discussion",
    ] = "speech"


class CivicLensResult(BaseModel):
    request: ResearchRequest
    selected_record: SpeechRecord
    speech_analysis: SpeechAnalysis
    longitudinal_analysis: LongitudinalAnalysis | None = None
    safety_review: SafetyReview


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    selected_record_id: str | None = None


class ChatResponse(BaseModel):
    message: str
