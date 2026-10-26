"""Find transcript candidates in Rev's public archive sitemap for the project roster.

Discovery results are leads only. The collector and manifest importer remain
separate so an unrelated political transcript cannot enter the campaign corpus.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
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
CAMPAIGN_TERMS = re.compile(
    r"campaign|convention|rnc|dnc|election|victory|primary|runoff|rally|stump|"
    r"presidential|nomination|speech|speaks-at",
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
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "MGT409-campaign-speech-discovery/1.0", "Accept-Encoding": "gzip"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        body = response.read()
        return gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body


def search_news(item: tuple[str, str, str]) -> list[dict[str, str]]:
    politician, state, topic = item
    query = f'"{politician}" {topic} -interview -floor -podcast'
    url = f"{NEWS_SEARCH}?{urllib.parse.urlencode({'q': query})}"
    root = ET.fromstring(fetch(url))
    leads = []
    relevant = re.compile(
        r"speech|transcript|campaign|convention|launch|remarks|victory|"
        r"concession|full text|dnc|rnc",
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
    prior_archive_reviews = {}
    if OUTPUT.is_file():
        with OUTPUT.open(encoding="utf-8", newline="") as handle:
            prior_archive_reviews = {row["source_url"]: row["review_status"] for row in csv.DictReader(handle)}
    prior_news_reviews = {}
    if NEWS_OUTPUT.is_file():
        with NEWS_OUTPUT.open(encoding="utf-8", newline="") as handle:
            prior_news_reviews = {row["candidate_id"]: row["review_status"] for row in csv.DictReader(handle)}
    with ROSTER.open(encoding="utf-8", newline="") as handle:
        roster = [(row["politician"], row["state"]) for row in csv.DictReader(handle)]
    root = ET.fromstring(fetch(SITEMAP))
    urls = [node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text]
    candidates = []
    for politician, state in roster:
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
    fields = ["candidate_id", "politician", "state", "source_url", "discovered_from", "review_status"]
    write_csv(OUTPUT, fields, candidates)
    print(f"Found {len(candidates)} archive candidates across {len({r['politician'] for r in candidates})} politicians: {OUTPUT}")

    queries = [(name, state, topic) for name, state in roster for topic in NEWS_TOPICS]
    news_leads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(search_news, item) for item in queries]
        for future in concurrent.futures.as_completed(futures):
            try:
                news_leads.extend(future.result())
            except Exception as exc:
                print(f"News search skipped after error: {exc}")
    deduplicated = {}
    for row in news_leads:
        prior = deduplicated.get(row["candidate_id"])
        if prior:
            prior["search_query"] += f"; {row['search_query']}"
        else:
            row["review_status"] = prior_news_reviews.get(row["candidate_id"], row["review_status"])
            deduplicated[row["candidate_id"]] = row
    news_leads = list(deduplicated.values())
    news_leads.sort(key=lambda row: (row["politician"], row["published"], row["headline"]))
    news_fields = ["candidate_id", "politician", "state", "search_query", "published", "headline", "publisher", "publisher_url", "news_result_url", "review_status"]
    write_csv(NEWS_OUTPUT, news_fields, news_leads)
    print(f"Found {len(news_leads)} news leads across {len({r['politician'] for r in news_leads})} politicians: {NEWS_OUTPUT}")


if __name__ == "__main__":
    main()
