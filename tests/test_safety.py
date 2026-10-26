"""Credential-free tests for deterministic source-grounding safeguards."""

from __future__ import annotations

import unittest
from datetime import date

from app.models import Citation
from app.workflow import retain_exact_source_quotes


class SafetyGuardTests(unittest.TestCase):
    def test_fabricated_quote_is_removed_from_analysis_evidence(self) -> None:
        source = "We should expand access to affordable health care for every family."
        exact = Citation(
            record_id="source-1",
            politician="John Cornyn",
            date=date(2024, 1, 1),
            quote="expand access to affordable health care",
            source_url="https://example.org/source",
        )
        fabricated = Citation(
            record_id="source-1",
            politician="John Cornyn",
            date=date(2024, 1, 1),
            quote="I will cut Medicare by half.",
            source_url="https://example.org/source",
        )

        retained, removed_count = retain_exact_source_quotes([exact, fabricated], source)

        self.assertEqual([exact], retained)
        self.assertEqual(1, removed_count)


if __name__ == "__main__":
    unittest.main()
