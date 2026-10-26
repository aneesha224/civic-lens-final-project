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
