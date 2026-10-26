# Speech collection status

Last checked: October 25, 2026.

The original page-level pass contains source-preserved captures from the
downloaded Congressional Record issues. It remains available as an audit
source, but it is not the analysis corpus.

## Complete-remark reconstruction

The page-level pass is retained as an audit source, but it is not the final
analysis corpus. Run `python scripts/reconstruct_complete_remarks.py` from the
Final Project directory to create `data/complete_remarks/` and
`data/complete_speech_records.csv`. The reconstruction follows each selected
speaker turn until the next speaker heading, including continuation pages, and
stores the inclusive source page range. These are complete Congressional Record
speaker turns, not claims about every speech given by a politician outside the
Congressional Record.

Current output: 1,061 complete source-preserved speaker remarks from 119
valid downloaded issues. Of these, 280 span multiple PDF pages. Sixteen
politicians are represented, each with at least five reconstructed remarks.
One cached source file (CREC-2019-01-07.pdf) is an HTML error page rather
than a PDF and is skipped by the rebuild script.

## Provenance rule

Each complete-remark record points to an official GovInfo PDF, an inclusive
source page range, and a local transcript file. The transcript file contains
text extracted from that PDF with pypdf. No transcript text was written by the
project. Boundary status is retained in the metadata so low-confidence cases
can be manually reviewed before analysis.

## Campaign speech collection

Campaign support is built into the corpus layer. Campaign records use a separate
source category and are imported through `scripts/import_campaign_speeches.py`.
The manifest now contains seven source-preserved full transcripts from four
politicians: Ted Cruz (3), Marco Rubio (2), Hakeem Jeffries (1), and John Cornyn
(1). Sources are TIME transcript pages recovered from Internet Archive captures
and Rev's transcript archive. The collector extracts the speech block and keeps
the original page capture; joint transcripts are limited to the named politician's
speaker section.

For the next pass, `scripts/discover_campaign_speeches.py` searches Rev's public
sitemap against all 16 roster names and writes `data/campaign_speeches/archive_candidates.csv`.
Candidate pages still require date, campaign-context, and transcript-boundary
review before they are added. TIME's dated sitemap and Internet Archive captures
also surfaced older transcripts that are missing from current page versions.

## Historical text corpus

Classical books will be added as a separate collection with its own source and rights metadata. Project Gutenberg, the Internet Archive, and the HathiTrust Digital Library are possible sources, but each work must be checked for public-domain status and a stable source record before inclusion.

