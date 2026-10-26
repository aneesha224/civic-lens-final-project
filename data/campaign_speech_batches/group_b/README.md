# Group B batch

Two distinct Ted Cruz public press-conference transcripts were extracted from Rev pages. Each .html file is the unchanged downloaded publisher page; each .txt contains only source-labelled Ted Cruz turns, retaining timestamps. transcript_path values are relative to this batch folder; remap to the main corpus captures folder when merging.

Tammy Duckworth 2020 DNC record: PBS source page labels this the full speech and provides an English SRT caption track. The original SRT is preserved as captures/tammy-duckworth-2020-dnc.speech.srt; the page capture is captures/tammy-duckworth-2020-dnc.html. Caption URL: https://ga.video.cdn.pbs.org/captions/newshour/8ccd42bb-04fe-46b8-af31-dfb2c9d72c93/captions/stmUG1_caption.srt. Date 2020-08-20 and the final-night context are stated on the PBS page. The plain text file removes only SRT cue numbers and timestamps.

Cory Booker 2016 DNC record: captures the complete structured transcript block from the TIME article. The app’s live-cache text parser only surfaced the article excerpt, but the preserved source HTML contains all transcript paragraphs after “Read a full transcript of his speech below.” The speech text runs from “Hello, Philadelphia” through the final “God bless America.” The source page was published on July 26 and identifies the speech as Monday night; event date is July 25, 2016.

## Kevin McCarthy public speeches

Two complete prepared public speeches were collected from archived Speaker.gov pages. The page HTML is preserved unchanged in `captures/`; each text file contains only the prepared speech paragraphs. Speaker.gov labels each transcript block “Remarks as prepared.” The event dates, venues, opening lines, and closing lines were checked against the archived source pages.

- **Kevin McCarthy — New York Stock Exchange address (April 17, 2023):** https://web.archive.org/web/20230417175517id_/https://www.speaker.gov/speaker-mccarthys-speech-at-the-new-york-stock-exchange/ — 127 source paragraphs, ending “...address this urgent challenge.”
- **Kevin McCarthy — Knesset address (May 1, 2023):** https://web.archive.org/web/20230501171609id_/https://www.speaker.gov/speaker-mccarthys-remarks-at-the-knesset/ — 136 source paragraphs, ending “God bless you. God bless Israel. And God bless our special relationship.”
