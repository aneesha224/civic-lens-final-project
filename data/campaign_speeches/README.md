# Campaign speech collection

Campaign records are kept separate from Congressional Record remarks and are
loaded by the app from data/campaign_speech_records.csv.

Only add a campaign transcript when:

- the full text is available from a reputable public source;
- the original URL is recorded;
- the date and campaign context are known;
- the local file is an exact source copy, not an AI reconstruction; and
- the record is marked complete or partial honestly.

The project roster contains 16 politicians. No single archive covers all of
their campaign speeches or other public remarks. When a user selects a name,
Civic Lens searches Bing's public results and Google News RSS for speech
transcripts, convention remarks, campaign events, and public addresses across
every election cycle mapped for the selected politician. It follows every
distinct result identified as a likely transcript, keeps source leads when a
full transcript is unavailable, and extracts text only from pages identified as
transcripts or full text. Search leads can also be loaded into the in-app reader;
the server fetches and extracts the page when it contains a complete transcript.
Short excerpts and ordinary article summaries remain citations, not speech
records. This collection is best-effort and changes as publishers add, remove,
or block pages.

On-demand results are cached as ordinary files under `live_cache/`: a search
index, JSON source metadata, the retrieved source HTML, and extracted text.
Search results are reused for 24 hours. This is a flat-file cache, not a
database. The existing CSV collection and Congressional Record corpus remain
separate and are not replaced. New extractions are labeled for source and
boundary review; source publication dates may differ from speech dates. Search
leads without transcript text can be retried through the in-app import action;
they are not presented as transcripts until a full text is retrieved.

The manual discovery scripts, election-cycle map, and reviewed office-campaign
leads remain available for curating a more carefully verified static collection.

The reviewed office-cycle leads currently match three imported transcripts to
their election campaigns: Ted Cruz's 2024 Senate race, Hakeem Jeffries's 2024
House race, and John Cornyn's 2026 Senate runoff. Video-only speeches remain
leads until a complete source transcript is available.


## October 25 historical source review milestone (superseded)

At the October 25 checkpoint, the curated non-Congressional Record manifest
contained 21 public speech and interview transcripts from nine politicians.
Eleven records had been added from source pages already captured by Civic Lens.
Their source pages were preserved beside the copied text in `captures/`. The
October 26 collection update below supersedes those historical counts and
records the 53-text manifest as of October 26.

That earlier pass added Elizabeth Warren’s 2018 election-night speech and 2019 Clark
Atlanta remarks; Bernie Sanders’s 2016 and 2020 convention speeches, 2019 Iowa
campaign rally, 2020 campaign suspension remarks, and 2019 television interview;
Cory Booker’s 2012 convention remarks and 2019 campaign kickoff; Nancy Pelosi’s
2020 convention speech; and Hakeem Jeffries’s remarks on the first 100 days of
the Trump administration. The Jeffries entry uses the official page’s April 30,
2025 publication date because its delivery date is not stated separately.

The app uses the same record IDs for reviewed static transcripts and their local
search-cache entries. When a reviewed copy is present, the app loads that copy
once instead of showing both the cached extraction and the curated transcript.


## October 26, 2026 public-text collection update (intermediate snapshot; superseded below)

The curated public-source corpus contains 93 transcript records from 15 of the 16 roster members. Ninety-one are complete and two remain partial. Current counts: Bernie Sanders 19 (18 complete), Jim Clyburn 16, Nancy Pelosi 10, Ted Cruz 7, Cory Booker 7, Marco Rubio 6, Elizabeth Warren 6, Hakeem Jeffries 6 (5 complete), Kirsten Gillibrand 4, Pat Toomey 3, Thom Tillis 3, Tammy Duckworth 2, Kevin McCarthy 2, John Cornyn 1, Rick Scott 1, and Gary Peters 0.

The user-set goal is at least 30 distinct complete public-source records per roster member, or 480 total. The collection is still short by 389 complete records. Do not count Congressional Record turns, short acknowledgments, duplicate event copies, excerpts, video-only pages, or pending search leads. The curated collection includes public speeches, prepared remarks, interviews, and press events. Recent batches added 15 Clyburn records; broadcast interviews for Duckworth, Gillibrand, and Toomey; speeches by Booker, Pelosi, Sanders, Warren, Jeffries, and Rick Scott; and McCarthy’s January 2021 remarks. The source pages and manual speaker/date boundary notes are preserved beside the transcript text.

The app also keeps a separate on-demand cache of source leads and extracted text. Cached items that still say boundary review is needed do not count as curated records. The discovery pass currently has 118 news leads and 21 Rev archive candidates; these remain leads, not transcript records. Reject summaries, excerpts, video-only pages, duplicate copies of the same event, and any text that does not preserve the source speaker boundaries. Keep incomplete source transcripts marked partial.

All curated texts have a direct source URL and preserved source-page capture. Transcript text is source-preserved and not generated by the project. The two partial records remain marked partial. The curated manifest currently has no duplicate source-text hashes.

## October 26, 2026 late manifest refresh

The current manifest contains 255 public-source transcript records across all
16 roster members. Of these, 253 are complete and two are partial. The target
is at least 30 distinct complete records per person. Elizabeth Warren (33),
Marco Rubio (30), and Nancy Pelosi (30) meet or exceed it; 230 additional
complete records are needed to bring every other person to 30. Gary Peters has
seven complete records. The
partial records belong to Bernie Sanders and Hakeem Jeffries.

The complete, partial, and remaining-to-30 counts for all 16 people are listed
in `../collection_live_tally.md`. The 93-record count and roster distribution
in the intermediate snapshot above are historical and have been superseded by
this manifest refresh. The current per-person counts are in the live tally. The manifest and transcript copies remain the current
curated collection; search leads and unreviewed batch files are not included.

