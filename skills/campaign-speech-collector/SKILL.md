---
name: campaign-speech-collector
description: Collect source-verifiable campaign speech transcripts for the Final Project roster, preserving provenance and refusing generated or unverifiable text.
metadata:
  short-description: Collect verified campaign speeches
---

# Campaign speech collector

Use this skill when expanding `data/campaign_speeches/` with campaign, convention,
stump, or election speeches.

Start with the archive index, then search dated publisher archives and news indexes
for roster members and campaign events that do not appear there. A page title or a
search result is only a lead: confirm the date, campaign setting, named speaker, and
actual speech opening and ending in the source page. Reject interviews, summaries,
broken templates, and pages whose title promises a transcript but whose body omits it.

Run from the `Final Project` directory:

```bash
python scripts/discover_campaign_speeches.py
python scripts/collect_campaign_speeches.py --seed-file data/campaign_speeches/seeds.csv
python scripts/import_campaign_speeches.py
```

The discovery script checks Rev's public transcript sitemap against all 16 roster
names and searches Google News RSS with separate queries for campaign launches,
announcements, suspensions, victories, concessions, and dated DNC/RNC events. It
deduplicates articles that match multiple queries and writes archive URLs to
`archive_candidates.csv` and news leads to `news_search_leads.csv`.

For requests limited to candidates running for a particular federal office, run
`python scripts/discover_office_campaign_speeches.py`. It uses
`office_campaign_cycles.csv` to associate a speech with a House or Senate race
year, checks that the source date falls near that cycle, and writes reviewed
results to `office_campaign_search_leads.csv`. Video-only sources stay leads and
must not be imported as transcript records.

Treat every search result as a lead. Resolve it to the publisher's direct page,
check the date and campaign context, and verify the speech's first and last lines.
For older TIME results, use the Internet Archive CDX index to locate saved source
pages. A narrow article-ID prefix plus a politician-name filter is effective when
the result's publication period is known; broad site-wide CDX searches can time
out. The collector downloads only URLs listed in `seeds.csv`. A seed must identify
the politician, event date, campaign context, and source URL. It preserves the
page and extracts a transcript block when present, including Rev transcript
bodies, source blockquotes, and legacy NPR `storytext` transcript paragraphs. It
never generates or repairs speech text.

Only promote a capture into `manifest.csv` after checking that its local text starts
and ends with the source speech and excludes adjacent speakers. The importer remains
the final schema and validation gate.
