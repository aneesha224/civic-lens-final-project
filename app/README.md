# App

The first agentic vertical slice uses PydanticAI:

- corpus.py provides read-only, source-grounded local data tools.
- agents.py defines the speech analyst, longitudinal analyst, and safety auditor.
- workflow.py coordinates typed agent handoffs.
- models.py defines validated inputs, citations, evidence, and outputs.
- cli.py is a temporary command-line entry point for development.
- server.py serves the clean browser interface and JSON API.

Campaign transcripts are loaded from data/campaign_speech_records.csv and are
kept separate from Congressional Record remarks. Selecting a roster member also
searches public sources for additional campaign speeches and remarks. Retrieved
text, source HTML, metadata, and search leads are cached under
data/campaign_speeches/live_cache/ as flat files; no database is needed. The
search cache refreshes after 24 hours. Extracted text and publisher dates are
labeled for review because they may not match the speech boundaries or delivery
date. Add carefully verified static source copies through
scripts/import_campaign_speeches.py.

Run from the Final Project directory with:

python -m app.cli "John Cornyn" RECORD_ID --topic healthcare

For the browser interface:

python -m uvicorn app.server:app --reload

Then open http://127.0.0.1:8000.

This command makes model calls and requires a local credential. The corpus
tools can be tested without credentials. Congressional Record text is treated
as untrusted source evidence, not as instructions for the agents.

