# Downloaded source documents

## CREC-2020-01-08.pdf

- Source: GovInfo, official Congressional Record daily edition
- URL: https://www.govinfo.gov/content/pkg/CREC-2020-01-08/pdf/CREC-2020-01-08.pdf
- Retrieved: October 24, 2026
- SHA-256: `5f6d5eb878710aa54ea58fd727b28f1d481619936a8c0e96ed07047c759ba091`
- Extraction: `scripts/extract_verified_speeches.py` using pypdf

The transcript files in `data/transcripts/` are page-level text extracted from this PDF. The extraction script does not generate, summarize, or paraphrase speech text. Page numbers and source URLs are recorded in `data/speech_records.csv`.

