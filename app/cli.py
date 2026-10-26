"""Small CLI for exercising the first agentic vertical slice."""

from __future__ import annotations

import argparse
import asyncio
import json

from .models import ResearchRequest
from .workflow import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Civic Lens research.")
    parser.add_argument("politician")
    parser.add_argument("record_id")
    parser.add_argument("--topic")
    parser.add_argument("--phrase")
    parser.add_argument(
        "--mode",
        default="speech",
        choices=["speech", "related_records", "language_change", "first_discussion"],
    )
    args = parser.parse_args()
    request = ResearchRequest(
        politician=args.politician,
        record_id=args.record_id,
        topic=args.topic,
        phrase=args.phrase,
        analysis_mode=args.mode,
    )
    result = asyncio.run(run_research(request))
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
