"""Find major speech leads for the federal offices in the project roster."""
from __future__ import annotations

import concurrent.futures
import csv
from email.utils import parsedate_to_datetime
import hashlib
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import certifi

CYCLES = Path("data/campaign_speeches/office_campaign_cycles.csv")
OUTPUT = Path("data/campaign_speeches/office_campaign_search_leads.csv")
GENERAL_LEADS = Path("data/campaign_speeches/news_search_leads.csv")
NEWS_SEARCH = "https://news.google.com/rss/search"
TOPICS = (
    "victory speech transcript",
    "election night speech full text",
    "concession speech transcript",
    "campaign announcement speech transcript",
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MGT409-office-campaign-speech-discovery/1.0"},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=25, context=context) as response:
        return response.read()


def search_news(item: tuple[str, str, str, int, str]) -> list[dict[str, str]]:
    politician, state, office, year, topic = item
    query = f'"{politician}" "{state}" {year} "{office}" {topic} -interview -floor -presidential'
    url = f"{NEWS_SEARCH}?{urllib.parse.urlencode({'q': query})}"
    root = ET.fromstring(fetch(url))
    full_name = politician.casefold()
    relevant_headline = re.compile(
        r"speech|transcript|full text|remarks|address|concession|victory|"
        r"election night|campaign launch|campaign announcement|rally|nomination",
        re.I,
    )
    rows = []
    for node in root.findall(".//item")[:10]:
        headline = node.findtext("title", "").strip()
        if full_name not in headline.casefold() or not relevant_headline.search(headline):
            continue
        published = node.findtext("pubDate", "").strip()
        try:
            publication_year = parsedate_to_datetime(published).year
        except (TypeError, ValueError):
            publication_year = year
        if not year - 1 <= publication_year <= year + 1:
            continue
        source = node.find("source")
        news_url = node.findtext("link", "").strip()
        key = f"{politician}|{office}|{year}|{headline}|{news_url}"
        rows.append({
            "candidate_id": f"office-news-{hashlib.sha1(key.encode()).hexdigest()[:12]}",
            "politician": politician,
            "state": state,
            "target_office": office,
            "election_year": str(year),
            "search_query": query,
            "published": published,
            "headline": headline,
            "publisher": source.text.strip() if source is not None and source.text else "",
            "publisher_url": source.attrib.get("url", "") if source is not None else "",
            "source_page_url": "",
            "news_result_url": news_url,
            "review_status": "lead only: confirm this is the named candidate's target-office campaign and verify full speech text",
        })
    return rows


def content_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    headline = row["headline"].strip()
    suffix = f" - {row['publisher']}"
    if headline.casefold().endswith(suffix.casefold()):
        headline = headline[:-len(suffix)].strip()
    return (
        row["politician"], row["election_year"], headline.casefold(),
        row["publisher_url"].casefold(),
    )


def main() -> None:
    with CYCLES.open(encoding="utf-8", newline="") as handle:
        cycles = list(csv.DictReader(handle))
    jobs = []
    for row in cycles:
        for raw_year in row["election_years"].split("|"):
            year = int(raw_year)
            jobs.extend(
                (row["politician"], row["state"], row["target_office"], year, topic)
                for topic in TOPICS
            )

    previous_reviews = {}
    previous_rows = []
    if OUTPUT.is_file():
        with OUTPUT.open(encoding="utf-8", newline="") as handle:
            previous_rows = list(csv.DictReader(handle))
            previous_reviews = {row["candidate_id"]: row["review_status"] for row in previous_rows}

    leads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(search_news, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            try:
                leads.extend(future.result())
            except Exception as exc:
                print(f"Search skipped after error: {exc}")

    # The broader search finds dated convention speeches; keep only those that
    # fall within a roster member's House or Senate election cycle.
    if GENERAL_LEADS.is_file():
        with GENERAL_LEADS.open(encoding="utf-8", newline="") as handle:
            general_leads = list(csv.DictReader(handle))
        cycle_map = {}
        for cycle in cycles:
            for raw_year in cycle["election_years"].split("|"):
                cycle_map.setdefault(cycle["politician"], []).append(
                    (cycle["state"], cycle["target_office"], int(raw_year))
                )
        for lead in general_leads:
            if not re.search(r"dnc|rnc|convention", lead["headline"], re.I):
                continue
            try:
                publication_year = parsedate_to_datetime(lead["published"]).year
            except (TypeError, ValueError):
                continue
            for state, office, year in cycle_map.get(lead["politician"], []):
                if not year - 1 <= publication_year <= year + 1:
                    continue
                key = f"{lead['candidate_id']}|{office}|{year}"
                rows_from_general = {
                    "candidate_id": f"office-general-{hashlib.sha1(key.encode()).hexdigest()[:12]}",
                    "politician": lead["politician"],
                    "state": state,
                    "target_office": office,
                    "election_year": str(year),
                    "search_query": lead["search_query"],
                    "published": lead["published"],
                    "headline": lead["headline"],
                    "publisher": lead["publisher"],
                    "publisher_url": lead["publisher_url"],
                    "source_page_url": "",
                    "news_result_url": lead["news_result_url"],
                    "review_status": "lead only: convention speech falls in this target-office election cycle; verify direct source and full text",
                }
                leads.append(rows_from_general)

    unique = {}
    content_keys = {}
    for row in leads:
        key = content_key(row)
        existing_id = content_keys.get(key)
        if existing_id:
            unique[existing_id]["search_query"] += f"; {row['search_query']}"
        elif row["candidate_id"] not in unique:
            row["review_status"] = previous_reviews.get(row["candidate_id"], row["review_status"])
            unique[row["candidate_id"]] = row
            content_keys[key] = row["candidate_id"]
        else:
            unique[row["candidate_id"]]["search_query"] += f"; {row['search_query']}"
    for row in previous_rows:
        if row["review_status"].startswith("lead only:"):
            continue
        key = content_key(row)
        existing_id = content_keys.get(key)
        if existing_id:
            existing = unique[existing_id]
            if row["source_page_url"] and not existing["source_page_url"]:
                unique[existing_id] = row
            elif row["review_status"]:
                existing["review_status"] = row["review_status"]
        elif row["candidate_id"] not in unique:
            unique[row["candidate_id"]] = row
            content_keys[key] = row["candidate_id"]

    rows = sorted(unique.values(), key=lambda row: (
        row["politician"], row["election_year"], row["published"], row["headline"]
    ))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "candidate_id", "politician", "state", "target_office", "election_year",
        "search_query", "published", "headline", "publisher", "publisher_url",
        "source_page_url", "news_result_url", "review_status",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Searched {len(jobs)} office-cycle queries; found {len(rows)} leads across {len({r['politician'] for r in rows})} politicians: {OUTPUT}")


if __name__ == "__main__":
    main()
