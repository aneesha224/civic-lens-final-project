# Speech collection status

Last checked: October 26, 2026.

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

Current output: 1,292 complete source-preserved speaker remarks from 119
valid downloaded issues. Of these, 367 span multiple PDF pages. Twenty-one
speaker names are represented, including all 16 roster members. Five roster
members previously missing from the extractor now have official source turns.
One cached source file (CREC-2019-01-07.pdf) is an HTML error page rather
than a PDF and is skipped by the rebuild script.

## Provenance rule

Each complete-remark record points to an official GovInfo PDF, an inclusive
source page range, and a local transcript file. The transcript file contains
text extracted from that PDF with pypdf. No transcript text was written by the
project. Boundary status is retained in the metadata so low-confidence cases
can be manually reviewed before analysis.

## Campaign speech collection

The curated public-source corpus is separate from the Congressional Record. Its
manifest contains 281 transcript records across all 16 roster members: 279
complete and two partial. Elizabeth Warren (33 complete), Marco Rubio (30), and
Nancy Pelosi (30) meet or exceed the goal of 30 complete records per person.
Another 206 complete records are needed to fill the individual gaps for the
other 12 politicians. Gary Peters has seven complete records. The two partial records are
for Bernie Sanders and Hakeem Jeffries.

The collection includes public addresses, prepared remarks, broadcast
interviews, press events, and speaker-isolated segments from multi-person
events. Congressional Record turns do not count toward the 30-record target.
See `collection_live_tally.md` for the complete roster-by-roster counts and
`campaign_speeches/README.md` for the source and boundary rules.

The app also keeps a separate on-demand cache of source leads and extracted
text. Cached items that still say boundary review is needed do not count as
curated records. The discovery pass currently has 118 news leads and 21 Rev
archive candidates; these remain leads, not transcript records. Reject
summaries, excerpts, video-only pages, duplicate copies of the same event, and
any text that does not preserve source speaker boundaries. Keep incomplete
source transcripts marked partial.

## Historical text corpus

Classical books will be added as a separate collection with its own source and rights metadata. Project Gutenberg, the Internet Archive, and the HathiTrust Digital Library are possible sources, but each work must be checked for public-domain status and a stable source record before inclusion.

