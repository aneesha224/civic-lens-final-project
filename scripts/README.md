# Scripts

Place repeatable setup, measurement, screenshot, and validation scripts here.

## Corpus reconstruction

`reconstruct_complete_remarks.py` reads every downloaded Congressional Record
issue in `data/source_pdfs/`, follows each target speaker turn across page
boundaries, and writes source-preserved complete remarks to
`data/complete_remarks/`. Its metadata output is
`data/complete_speech_records.csv`. The earlier page-level files remain in
`data/transcripts/` for provenance comparison.

