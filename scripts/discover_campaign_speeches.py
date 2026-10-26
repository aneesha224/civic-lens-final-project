"""Find transcript candidates in Rev's public archive sitemap for the project roster.

Discovery results are leads only. The collector and manifest importer remain
separate so an unrelated political transcript cannot enter the campaign corpus.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import argparse
import re
import ssl
import concurrent.futures
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import certifi

ROSTER = Path("data/politicians.csv")
OUTPUT = Path("data/campaign_speeches/archive_candidates.csv")
NEWS_OUTPUT = Path("data/campaign_speeches/news_search_leads.csv")
SITEMAP = "https://www.rev.com/sitemap.xml"
NEWS_SEARCH = "https://news.google.com/rss/search"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
CAMPAIGN_TERMS = re.compile(
    r"campaign|convention|rnc|dnc|election|victory|primary|runoff|rally|stump|"
    r"presidential|nomination|speech|speaks-at|interview|town-hall|press-conference|public-remarks",
    re.I,
)
NEWS_TOPICS = (
    "campaign launch speech full text",
    "campaign announcement speech full text",
    "campaign suspension speech transcript",
    "campaign concession speech transcript",
    "campaign victory speech full text",
    "2012 Democratic National Convention speech full text",
    "2012 Republican National Convention speech full text",
    "2016 Democratic National Convention speech transcript",
    "2016 Republican National Convention speech transcript",
    "2020 Democratic National Convention speech transcript",
    "2020 Republican National Convention speech transcript",
    "2024 Democratic National Convention speech transcript",
    "2024 Republican National Convention speech transcript",
    "public remarks full transcript",
    "town hall transcript",
    "press conference transcript",
    "campaign interview transcript",
    "keynote address speech transcript",
)


def fetch(url: str, timeout: float = 12) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "MGT409-campaign-speech-discovery/1.0", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        body = response.read()
        return gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body


def search_news(item: tuple[str, str, str], timeout: float = 12) -> list[dict[str, str]]:
    politician, state, topic = item
    query = f'"{politician}" {topic} -floor -podcast'
    url = f"{NEWS_SEARCH}?{urllib.parse.urlencode({'q': query})}"
    root = ET.fromstring(fetch(url, timeout))
    leads = []
    relevant = re.compile(
        r"speech|transcript|campaign|convention|launch|remarks|victory|"
        r"concession|full text|dnc|rnc|interview|town hall|press conference|keynote",
        re.I,
    )
    surname = politician.split()[-1].casefold()
    for node in root.findall(".//item")[:10]:
        title = node.findtext("title", "").strip()
        if not relevant.search(title) or surname not in title.casefold():
            continue
        source = node.find("source")
        result_url = node.findtext("link", "").strip()
        key = f"{politician}|{title}|{result_url}"
        leads.append({
            "candidate_id": f"news-{hashlib.sha1(key.encode()).hexdigest()[:12]}",
            "politician": politician,
            "state": state,
            "search_query": query,
            "published": node.findtext("pubDate", "").strip(),
            "headline": title,
            "publisher": source.text.strip() if source is not None and source.text else "",
            "publisher_url": source.attrib.get("url", "") if source is not None else "",
            "news_result_url": result_url,
            "review_status": "lead only: inspect publisher page and verify full speech boundaries",
        })
    return leads


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find transcript leads for all or selected roster members.")
    parser.add_argument("--politicians", nargs="+", help="Limit News searches to these exact roster names; other saved leads are retained.")
    parser.add_argument("--workers", type=int, default=12, help="Concurrent News RSS searches (1–16; default: 12).")
    parser.add_argument("--timeout-seconds", type=float, default=12, help="Timeout per web request (default: 12 seconds).")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        raise SystemExit("--workers must be between 1 and 16")
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be greater than zero")

    prior_archive_rows = []
    if OUTPUT.is_file():
        with OUTPUT.open(encoding="utf-8", newline="") as handle:
            prior_archive_rows = list(csv.DictReader(handle))
    prior_archive_reviews = {row["source_url"]: row["review_status"] for row in prior_archive_rows}
    prior_news_rows = []
    if NEWS_OUTPUT.is_file():
        with NEWS_OUTPUT.open(encoding="utf-8", newline="") as handle:
            prior_news_rows = list(csv.DictReader(handle))
    prior_news_reviews = {row["candidate_id"]: row["review_status"] for row in prior_news_rows}
    with ROSTER.open(encoding="utf-8", newline="") as handle:
        roster = [(row["politician"], row["state"]) for row in csv.DictReader(handle)]
    roster_by_name = {name: state for name, state in roster}
    selected_names = set(args.politicians or roster_by_name)
    unknown_names = selected_names - roster_by_name.keys()
    if unknown_names:
        raise SystemExit(f"Unknown roster name(s): {', '.join(sorted(unknown_names))}")
    selected_roster = [(name, roster_by_name[name]) for name in roster_by_name if name in selected_names]

    root = ET.fromstring(fetch(SITEMAP, args.timeout_seconds))
    urls = [node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text]
    candidates = []
    for politician, state in selected_roster:
        name_slug = re.sub(r"[^a-z0-9]+", "-", politician.lower()).strip("-")
        for url in urls:
            path = url.lower().split("?")[0]
            if "/transcripts/" not in path or name_slug not in path or not CAMPAIGN_TERMS.search(path):
                continue
            candidates.append({
                "candidate_id": f"rev-{hashlib.sha1(url.encode()).hexdigest()[:12]}",
                "politician": politician,
                "state": state,
                "source_url": url,
                "discovered_from": SITEMAP,
                "review_status": prior_archive_reviews.get(url, "candidate: verify campaign context and full speech"),
            })
    current_archive_urls = {row["source_url"] for row in candidates}
    preserved_archive = [
        row for row in prior_archive_rows
        if row["politician"] not in selected_names
        or (row["source_url"] not in current_archive_urls and not row["review_status"].startswith("candidate:"))
    ]
    candidates = preserved_archive + candidates
    candidates.sort(key=lambda row: (row["politician"], row["source_url"]))
    fields = ["candidate_id", "politician", "state", "source_url", "discovered_from", "review_status"]
    write_csv(OUTPUT, fields, candidates)
    print(f"Found {len(candidates)} archive candidates across {len({r['politician'] for r in candidates})} politicians: {OUTPUT}")

    queries = [(name, state, topic) for name, state in selected_roster for topic in NEWS_TOPICS]
    news_leads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(search_news, item, args.timeout_seconds) for item in queries]
        for future in concurrent.futures.as_completed(futures):
            try:
                news_leads.extend(future.result())
            except Exception as exc:
                print(f"News search skipped after error: {exc}")
    # Keep prior leads even if a later RSS query is temporarily blocked or omits them.
    deduplicated = {row["candidate_id"]: row for row in prior_news_rows}
    for row in news_leads:
        prior = deduplicated.get(row["candidate_id"])
        if prior:
            prior["search_query"] += f"; {row['search_query']}"
        else:
            prior_status = prior_news_reviews.get(row["candidate_id"])
            if prior_status and not prior_status.startswith("lead only:"):
                row["review_status"] = prior_status
            if row["candidate_id"] not in deduplicated:
                deduplicated[row["candidate_id"]] = row
    news_leads = list(deduplicated.values())
    news_leads.sort(key=lambda row: (row["politician"], row["published"], row["headline"]))
    news_fields = ["candidate_id", "politician", "state", "search_query", "published", "headline", "publisher", "publisher_url", "news_result_url", "review_status"]
    write_csv(NEWS_OUTPUT, news_fields, news_leads)
    print(f"Found {len(news_leads)} news leads across {len({r['politician'] for r in news_leads})} politicians: {NEWS_OUTPUT}")


if __name__ == "__main__":
    main()
