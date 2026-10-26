# Final Project

An AI agent app that does something useful for real people.

## Status

Corpus reconstruction is complete for the currently downloaded Congressional
Record issues. The analysis corpus contains 1,061 source-preserved remarks from
119 issues dated January 2011 through December 2023. The app also includes 10
curated campaign transcripts dated August 2012 through May 2026, stored
separately from the Congressional Record. Selecting a politician starts a live
public-source search across that person's listed election cycles; coverage is
not continuous or exhaustive and does not form a uniform 2000–2026 archive.
Complete transcripts load into the speech menu as they are retrieved. The
importer recognizes known transcript archive URLs even when a result headline
does not use the word “transcript,” and excludes page scripts and styles from
speech text. Results are cached as flat files under
`data/campaign_speeches/live_cache/`, refresh after 24 hours, and require no
database.

## Run locally

1. Create and activate a virtual environment: `python3 -m venv .venv` and `source .venv/bin/activate`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` in this folder, or configure a `.env` one level above. Add `PORTKEY_API_KEY` or `OPENAI_API_KEY` for AI analysis and chat.
4. Start Civic Lens: `python -m uvicorn app.server:app --reload`.
5. Open `http://127.0.0.1:8000`.

## Publish on Render

The `render.yaml` Blueprint runs Civic Lens as a public web service. Start with
[Deploy to Render](https://render.com/deploy?repo=https://github.com/aneesha224/civic-lens-final-project),
or open Render and choose **New → Blueprint**. To deploy:

1. Use the [Civic Lens GitHub repository](https://github.com/aneesha224/civic-lens-final-project).
   The project files are already at its root. Keep `.env` out of Git;
   `.gitignore` already excludes it.
2. Connect the repository to Render and apply the `render.yaml` settings.
   Render creates the service and provides its public URL.
3. Enter `PORTKEY_API_KEY` as a secret in the Render setup prompt or the
   service's Environment settings. Do not put the key in `render.yaml` or Git.
   Without it, visitors can browse speeches, but AI analysis and chat are
   unavailable.

The free service may sleep when idle, so its first request after a quiet period
can take longer. Its filesystem is temporary: transcripts discovered while the
service runs may need to be fetched again after a restart or redeploy.

Browsing the corpus and opening source transcripts work without a model key.
Public-source discovery needs an internet connection. Retrieved transcripts
appear in the in-app reader. Search leads have a **Load transcript into Civic
Lens** action that fetches and extracts full speech text when the linked page
contains it; the original source remains available as a citation. Newly
extracted text is labeled for source and boundary review, and a publisher's
publication date can differ from the speech date. AI analysis and the page guide
require a configured key. The default model is
`gpt-6-luna`; set `AI_MODEL` in `.env` only when using another supported model.

## Rebuild the source corpus

From this directory, run:

python scripts/reconstruct_complete_remarks.py

This reads data/source_pdfs/, follows each selected speaker turn until the next
speaker or Congressional Record section boundary, and writes complete
source-preserved remarks to data/complete_remarks/. Metadata is written to
data/complete_speech_records.csv. The original page-level files in
data/transcripts/ remain available for provenance comparison.

The corpus represents complete Congressional Record speaker remarks in the
collected issue set. It does not represent every speech a politician gave
outside the Congressional Record.

## Required deliverables

- `report.html`: self-contained 10–15 page report.
- `slides.html`: self-contained reveal.js deck with no more than 10 slides.
- `app/`: application code and supporting assets.
- `tests/`: checks for core behavior and safety defenses.
- `evidence/`: screenshots, measured token usage, cost calculations, and test results.

## Configuration

The app should load `PORTKEY_API_KEY` or `OPENAI_API_KEY` from `.env` in this folder, then from the parent folder when run from a fresh submission clone. Never commit real credentials.

