"""Credential-free checks for the first PydanticAI vertical slice."""

from __future__ import annotations

import asyncio
import unittest

from pydantic_ai.models.test import TestModel

from app.agents import ResearchDeps, speech_analyst
from app.corpus import CorpusStore
from app.models import ResearchRequest


class AgentTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = CorpusStore()

    def test_corpus_has_reconstructed_records_and_exact_text(self) -> None:
        record = self.corpus.records[0]
        text = self.corpus.read_text(record)
        self.assertTrue(text.strip())
        self.assertIn(record.politician.split()[-1].upper(), text.upper())
        congressional = [r for r in self.corpus.records if r.source_category == "congressional_record"]
        campaign = [r for r in self.corpus.records if r.source_category == "campaign"]
        self.assertEqual(len(congressional), 1061)
        curated_campaign = [r for r in campaign if not r.transcript_status.startswith("on-demand v5 transcript;")]
        live_campaign = [r for r in campaign if r.transcript_status.startswith("on-demand v5 transcript;")]
        self.assertEqual(len(curated_campaign), 10)
        for live_record in live_campaign:
            self.assertTrue(self.corpus.read_text(live_record).strip())
        campaign_record = self.corpus.get("duckworth-2012-dnc")
        self.assertTrue(self.corpus.read_text(campaign_record).startswith("My name is Tammy Duckworth."))

    def test_request_rejects_unknown_analysis_mode(self) -> None:
        with self.assertRaises(ValueError):
            ResearchRequest(
                politician="John Cornyn",
                record_id="example",
                analysis_mode="unsupported",
            )

    def test_speech_agent_returns_typed_output_without_api_call(self) -> None:
        record = self.corpus.records[0]

        async def run() -> object:
            with speech_analyst.override(model=TestModel(call_tools=[])):
                result = await speech_analyst.run(
                    f"Analyze {record.record_id}",
                    deps=ResearchDeps(self.corpus),
                )
            return result.output

        output = asyncio.run(run())
        self.assertEqual(type(output).__name__, "SpeechAnalysis")


if __name__ == "__main__":
    unittest.main()
