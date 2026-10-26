# Speech corpus: first-pass design

## Scope

This first pass covers two qualifying federal politicians from each of the ten states with the largest House delegations under the current apportionment: California, Texas, Florida, New York, Pennsylvania, Illinois, Ohio, Georgia, North Carolina, and Michigan.

The roster uses a practical definition of prominent: a person who held elected federal office and has a substantial public record in Congress or the presidency. To qualify for this project, the person’s federal elected career must have begun in 2000 or later and lasted at least ten years by October 24, 2026. A state or local office before the federal career does not disqualify them, but the dataset records the federal start year explicitly.

## Sampling rule

The target is 24 speech records per politician: two substantial public statements per year across twelve sampled years. The years are the first federal-election year, the most recent year, and ten evenly spaced years between them. When a year has no suitable speech, the nearest available year is used and documented in `speech_records.csv`.

Each politician should have:

- six floor or hearing remarks from the Congressional Record;
- six campaign, convention, or election speeches;
- six policy or issue speeches;
- six nationally important remarks, interviews, addresses, or official statements.

The current roster contains 16 politicians, so the original target was 384 records. The first collection pass now exceeds that target with 747 page-level records for 15 politicians. Transcript acquisition should proceed source by source and should never invent missing text. `speech_records.csv` is the audit table for that process.

## Source priority

1. Congressional Record and official congressional websites.
2. Presidential archives and the American Presidency Project.
3. Official campaign or government archives.
4. C-SPAN or reputable news transcript archives.
5. Secondary databases only when the original source is linked and the transcript can be checked.

Every record needs a stable URL, date, venue, speaker, source type, and a note about whether the text is a full transcript, excerpt, or video-linked transcript.

## Important limitations

This is a research corpus, not a claim that every public statement by these people has been collected. The app must display coverage limits. “Contradiction” is an analytical hypothesis requiring context and human review; it is not a fact established by the presence of two different quotations.

