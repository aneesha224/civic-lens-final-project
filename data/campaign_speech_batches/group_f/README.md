# AWPC additional speech batch

Thirteen new full speech records from the Archives of Women’s Political Communication (AWPC) at Iowa State University. Each source transcript page is preserved as HTML beside a text extract; AWPC’s filtered index pages are saved under `captures/archive-index/`.

The current AWPC archive exposes speaker filters at `/speeches?person=...`. I reviewed every result page for Kirsten Gillibrand (14 results, one page), Tammy Duckworth (8 results, one page), Elizabeth Warren (79 results, four pages), and Nancy Pelosi (34 results, two pages). I compared the listed source URLs with the central manifest and staged batches A–E before selecting records. Gillibrand and Duckworth had no additional result pages.

The staged rows are distinct, complete public speeches or remarks, including campaign events, commencement addresses, convention speeches, and Pelosi’s public remarks in Taipei. The extracts remove AWPC’s explanatory introductions and source citations where those appeared alongside the speech. They preserve the speech wording and paragraph boundaries. The records remain staged; the central manifest was not edited.

Floor speeches, interviews, short fragments under 250 words, and multi-speaker transcripts without a sufficiently distinct full speech section were excluded. This includes Gillibrand’s Senate floor remarks on Equal Pay Day and the multi-senator 2016 DNC transcript. Duckworth’s 2020 DNC speech was eligible and is included.

## Records

- Kirsten Gillibrand — Power of Women Speech (2018-04-13, 811 words)
- Tammy Duckworth — Democratic National Convention Remarks (2020-08-20, 494 words)
- Elizabeth Warren — Remarks at the 2024 Democratic National Convention (2024-08-22, 445 words)
- Elizabeth Warren — New York City Rally (2019-09-16, 3,934 words)
- Elizabeth Warren — National Press Club Speech (2018-08-21, 4,242 words)
- Elizabeth Warren — Remarks at the 2016 Democratic National Convention (2016-07-25, 2,057 words)
- Elizabeth Warren — Keynote at Netroots Nation (2015-07-18, 3,138 words)
- Elizabeth Warren — Remarks at the California State Democratic Convention (2015-05-16, 2,107 words)
- Elizabeth Warren — Framingham State University Commencement Address (2013-05-19, 1,713 words)
- Elizabeth Warren — Victory Speech (2012-11-06, 924 words)
- Elizabeth Warren — Address at the 2012 Democratic National Convention (2012-09-05, 1,634 words)
- Nancy Pelosi — Remarks at the 2024 Democratic National Convention (2024-08-21, 514 words)
- Nancy Pelosi — We Will Not Abandon Taiwan (2022-08-03, 1,884 words)

CSV transcript paths are relative to this batch folder and should be remapped under `data/campaign_speeches/captures/` if the batch is merged.
