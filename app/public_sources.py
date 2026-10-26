"""On-demand discovery of public speech transcripts and source leads."""
from __future__ import annotations

import concurrent.futures
import base64
import csv
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
import re
import ssl
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import certifi

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = PROJECT_ROOT / "data" / "campaign_speeches" / "live_cache"
RECORDS_ROOT = CACHE_ROOT / "records"
INDEX_PATH = CACHE_ROOT / "search_index.json"
CYCLES_PATH = PROJECT_ROOT / "data" / "campaign_speeches" / "office_campaign_cycles.csv"
ROSTER_PATH = PROJECT_ROOT / "data" / "politicians.csv"
RSS_URL = "https://news.google.com/rss/search"
CACHE_HOURS = 24
SEARCH_VERSION = 9
TRANSCRIPT_ARCHIVES = {"presidentialrhetoric.com", "americanrhetoric.com", "awpc.cattcenter.iastate.edu", "rev.com"}
IGNORED_TRANSCRIPT_ELEMENTS = {"script", "style", "noscript", "iframe", "svg"}
PROMO_PREFIXES = (
    "huffpost holds power accountable", "already a member?", "follow this section",
    "update your preferences", "follow this tag", "follow this author",
    "this purchase is available", "c-span.org offers links", "please note that questions",
    "stream pbs", "support your local pbs", "from cultural festivals",
    "visit the official pbs shop", "luckily for you, we deliver",
    "subscribe to our blog today", "a confirmation email is on its way",
    "please refresh your page", "please refresh your browser", "other wral top stories",
)


def _fetch(url: str, timeout: int = 8) -> tuple[str, bytes]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CivicLens-public-speech-search/1.0", "Accept": "text/html,application/rss+xml,application/xml"},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.geturl(), response.read(5_000_000)


def _plain(value: str) -> str:
    value = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


class TranscriptParser(HTMLParser):
    """Extract speech-like blocks from common transcript archive layouts."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ignored_depth = 0
        self.active: list[tuple[int, str, list[str]]] = []
        self.candidates: list[tuple[str, str]] = []
        self.quote_depth = 0
        self.quote_parts: list[str] = []
        self.paragraph_depth: int | None = None
        self.paragraphs: list[str] = []
        self.current_paragraph: list[str] | None = None
        self.all_paragraphs: list[str] = []
        self.general_paragraph: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        classes = set((attrs_map.get("class") or "").split())
        self.stack.append(tag)
        if self.ignored_depth or tag in IGNORED_TRANSCRIPT_ELEMENTS:
            if tag in IGNORED_TRANSCRIPT_ELEMENTS:
                self.ignored_depth += 1
            return
        if tag == "div":
            if "blog-text-rich-text" in classes:
                self.active.append((len(self.stack), "Rev transcript", []))
            elif attrs_map.get("id") == "storytext":
                self.paragraph_depth = len(self.stack)
                self.paragraphs = []
            elif "paragraph-widget--text-content" in classes:
                self.paragraph_depth = len(self.stack)
                self.paragraphs = []
            elif classes.intersection({"article-body", "article__body", "article-content", "entry-content", "transcript-body"}):
                self.active.append((len(self.stack), "publisher article body", []))
        if tag == "blockquote":
            self.quote_depth += 1
        if tag == "p" and self.paragraph_depth is not None:
            self.current_paragraph = []
        if tag == "p":
            self.general_paragraph = []
        if tag in {"p", "br"}:
            for _, _, parts in self.active:
                parts.append("\n")
            if self.quote_depth:
                self.quote_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_TRANSCRIPT_ELEMENTS and self.ignored_depth:
            self.ignored_depth -= 1
        if self.ignored_depth:
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index] == tag:
                    self.stack = self.stack[:index]
                    break
            return
        if tag == "p" and self.current_paragraph is not None:
            text = re.sub(r"\s+", " ", "".join(self.current_paragraph)).strip()
            if text and not text.casefold().startswith("speech from "):
                self.paragraphs.append(text)
            self.current_paragraph = None
        if tag == "p" and self.general_paragraph is not None:
            text = re.sub(r"\s+", " ", "".join(self.general_paragraph)).strip()
            if len(text) > 35:
                self.all_paragraphs.append(text)
            self.general_paragraph = None
        if tag == "blockquote" and self.quote_depth:
            self.quote_depth -= 1
        if tag == "div":
            if self.paragraph_depth == len(self.stack):
                body = "\n\n".join(self.paragraphs)
                if body:
                    self.candidates.append(("university/archive transcript", body))
                self.paragraph_depth = None
                self.current_paragraph = None
            closing = [item for item in self.active if item[0] == len(self.stack)]
            for _, label, parts in closing:
                self.candidates.append((label, "".join(parts)))
            self.active = [item for item in self.active if item[0] != len(self.stack)]
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.paragraph_depth is not None and self.current_paragraph is not None:
            self.current_paragraph.append(data)
        if self.general_paragraph is not None:
            self.general_paragraph.append(data)
        for _, _, parts in self.active:
            parts.append(data)
        if self.quote_depth:
            self.quote_parts.append(data)

    def extract(self, raw: bytes, *, transcript_title: bool, politician: str) -> tuple[str, str] | None:
        self.feed(raw.decode("utf-8", errors="replace"))
        if self.quote_parts:
            self.candidates.append(("publisher transcript blockquote", "".join(self.quote_parts)))
        if transcript_title and self.all_paragraphs:
            article = "\n\n".join(self.all_paragraphs)
            if len(article) > 700:
                self.candidates.append(("publisher transcript paragraphs", article))
        choices = []
        for source, candidate in self.candidates:
            text = re.sub(r"Copyright Disclaimer\s+Under Title 17.*?infringing\.?", "", candidate, flags=re.I | re.S)
            paragraphs = []
            for paragraph in re.split(r"\n\s*\n+", text):
                paragraph = re.sub(r"\s+", " ", paragraph).strip()
                if not paragraph or paragraph.casefold().startswith(PROMO_PREFIXES):
                    continue
                if re.search(r"document\.getElement(?:sByClassName|ById)|addEventListener\s*\(|(?:const|let|var)\s+[\w$]+\s*=", paragraph, re.I):
                    continue
                paragraphs.append(paragraph)
            text = "\n\n".join(paragraphs)
            if len(text) >= 700:
                choices.append((source, text))
        choices.sort(key=lambda item: len(item[1]), reverse=True)
        if not choices:
            return None
        best_source, best_text = choices[0]
        # If the page contains time-coded multiple speakers, keep the named speaker's segment.
        heads = list(re.finditer(r"(?m)^([A-Z][A-Za-z .'-]+)\s+\(\d{2}:\d{2}\):\s*", best_text))
        match = next((i for i, head in enumerate(heads) if politician.casefold() in head.group(1).casefold()), None)
        if match is not None:
            start = heads[match].start()
            end = heads[match + 1].start() if match + 1 < len(heads) else len(best_text)
            best_text = best_text[start:end].strip()
        return (best_source, best_text) if len(best_text) >= 700 else None


def _queries(politician: str) -> list[str]:
    queries = [
        f'"{politician}" campaign speech transcript',
        f'"{politician}" convention speech transcript',
        f'"{politician}" victory speech transcript',
        f'"{politician}" campaign launch announcement speech full text',
        f'"{politician}" campaign rally speech transcript',
        f'"{politician}" election night remarks transcript',
        f'"{politician}" public address remarks transcript',
        f'"{politician}" interview transcript full text',
        f'"{politician}" Face the Nation transcript',
        f'"{politician}" Meet the Press transcript',
        f'"{politician}" This Week transcript',
        f'"{politician}" 60 Minutes transcript',
        f'"{politician}" town hall transcript',
        f'"{politician}" press conference transcript',
        f'"{politician}" public remarks transcript',
    ]
    years: list[int] = []
    try:
        with CYCLES_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["politician"].casefold() == politician.casefold():
                    years.extend(int(year) for year in row["election_years"].split("|") if year)
    except OSError:
        pass
    for year in sorted(set(years), reverse=True):
        queries.append(f'"{politician}" {year} campaign speech OR remarks transcript')
    return queries


def _search_one(query: str) -> list[dict[str, str]]:
    url = RSS_URL + "?" + urllib.parse.urlencode({"q": query})
    try:
        final_url, body = _fetch(url, timeout=8)
        root = ET.fromstring(body)
    except Exception:
        return []
    rows = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        description = _plain(item.findtext("description", ""))
        if not title or not link:
            continue
        if not re.search(r"speech|transcript|full text|remarks|address|victory|concession|election night|campaign|convention|rally", title, re.I):
            continue
        if politician_surname(query) not in title.casefold():
            continue
        if re.search(r"podcast|floor speech|senate speech|filibuster|hearing|opinion|highlights", title, re.I):
            continue
        source = item.find("source")
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", "")).date().isoformat()
        except (TypeError, ValueError):
            published = ""
        rows.append({
            "title": title,
            "publisher": source.text.strip() if source is not None and source.text else "",
            "publisher_url": source.attrib.get("url", "") if source is not None else "",
            "published": published,
            "news_url": link,
            "description": description[:500],
            "search_query": query,
        })
    return rows


def politician_surname(query: str) -> str:
    match = re.search(r'"([^"]+)"', query)
    return match.group(1).split()[-1].casefold() if match else ""


class BingResultsParser(HTMLParser):
    """Collect direct publisher links from Bing's public HTML results."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.result_depth: int | None = None
        self.current: dict[str, Any] | None = None
        self.anchor: dict[str, str] | None = None
        self.results: list[dict[str, str]] = []
        self.in_heading = 0

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID_TAGS:
            self.depth += 1
        values = dict(attrs)
        if tag == "h2":
            self.in_heading += 1
        if tag == "li" and "b_algo" in (values.get("class") or "").split():
            self.result_depth = self.depth
            self.current = {"title": "", "url": "", "text": "", "links": []}
        if self.current is not None and tag == "a":
            self.anchor = {"href": values.get("href") or "", "text": "", "heading": str(self.in_heading > 0)}

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"] += " " + data
        if self.anchor is not None:
            self.anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.anchor is not None and self.current is not None:
            link = self.anchor["href"]
            parsed = urllib.parse.urlparse(link)
            if parsed.netloc.endswith("bing.com"):
                encoded = urllib.parse.parse_qs(parsed.query).get("u", [""])[0]
                if encoded.startswith("a1"):
                    try:
                        link = base64.urlsafe_b64decode(encoded[2:] + "===").decode("utf-8", errors="replace")
                    except (ValueError, base64.binascii.Error):
                        link = ""
            host = urllib.parse.urlparse(link).netloc.casefold()
            if link.startswith(("https://", "http://")) and host and not host.endswith("bing.com"):
                self.current["links"].append({
                    "url": link,
                    "title": re.sub(r"\s+", " ", self.anchor["text"]).strip(),
                    "heading": self.anchor["heading"],
                })
            self.anchor = None
        if tag == "li" and self.result_depth == self.depth and self.current is not None:
            links = self.current["links"]
            link = next((item for item in links if item["heading"] == "True"), links[0] if links else None)
            if link:
                self.results.append({
                    "title": link["title"],
                    "url": link["url"],
                    "text": re.sub(r"\s+", " ", self.current["text"]).strip(),
                })
            self.current = None
            self.result_depth = None
        if tag == "h2" and self.in_heading:
            self.in_heading -= 1
        if tag not in self.VOID_TAGS:
            self.depth = max(0, self.depth - 1)


def _search_bing(query: str) -> list[dict[str, str]]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query})
    try:
        _, body = _fetch(url, timeout=8)
    except Exception:
        return []
    parser = BingResultsParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    surname = politician_surname(query)
    results = []
    for item in parser.results:
        title = _plain(item["title"])
        description = _plain(item["text"])
        if surname not in title.casefold():
            continue
        if not re.search(r"speech|transcript|full text|remarks|address|victory|concession|campaign|convention|rally", title, re.I):
            continue
        if re.search(r"podcast|floor speech|senate speech|filibuster|hearing|opinion|highlights", title, re.I):
            continue
        host = urllib.parse.urlparse(item["url"]).netloc
        results.append({
            "title": title,
            "publisher": host.removeprefix("www."),
            "publisher_url": "https://" + host,
            "published": "",
            "news_url": item["url"],
            "description": description[:500],
            "search_query": query,
        })
    return results


def _is_full_text_lead(lead: dict[str, str]) -> bool:
    title = lead.get("title", "")
    if re.search(r"podcast|floor speech|senate speech|filibuster|hearing|opinion|highlights|roundup", title, re.I):
        return False
    explicit_text = re.search(
        r"transcript|full\s+(?:speech|text|remarks|address)|read.{0,100}\b(?:full\s+)?(?:speech|remarks|address|text)\b|speech text|remarks as prepared|prepared remarks|speech\s*\([^)]*text",
        title,
        re.I,
    )
    host_url = lead.get("publisher_url") or lead.get("news_url", "")
    host = urllib.parse.urlparse(host_url).netloc.casefold().removeprefix("www.")
    source_path = urllib.parse.urlparse(lead.get("news_url", "")).path.casefold()
    archive = host in TRANSCRIPT_ARCHIVES and (
        re.search(r"speech|remarks|address", title, re.I)
        or "/transcripts/" in source_path
    )
    return bool(explicit_text or archive)


def _load_index() -> dict[str, Any]:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def import_public_speech(politician: str, source_url: str) -> dict[str, Any]:
    """Fetch a displayed search result and add its transcript to the local reader."""
    key = politician.casefold()
    index = _load_index()
    cached = index.get(key) or {}
    lead = next((item for item in cached.get("leads", [])
                 if source_url in {item.get("news_url"), item.get("source_url")}), None)
    if lead is None:
        raise ValueError("This search result expired. Choose the politician again and retry.")

    fetch_url = lead.get("news_url") or source_url
    parsed = urllib.parse.urlparse(fetch_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("This source does not have a valid public web address.")
    try:
        final_url, html_body = _fetch(fetch_url, timeout=9)
    except Exception as error:
        raise RuntimeError("The publisher page could not be fetched right now.") from error

    manifest_path = PROJECT_ROOT / "data" / "campaign_speeches" / "manifest.csv"
    try:
        with manifest_path.open(encoding="utf-8", newline="") as handle:
            existing = next((row for row in csv.DictReader(handle)
                             if row.get("politician", "").casefold() == key
                             and row.get("source_url") == final_url), None)
        if existing:
            lead["record_id"] = existing["record_id"]
            lead["status"] = "Full transcript is already in the Civic Lens reader"
            INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
            return existing
    except OSError:
        pass

    # Return an existing local transcript when this source was already collected.
    for meta_path in RECORDS_ROOT.glob("*.json"):
        try:
            row = json.loads(meta_path.read_text(encoding="utf-8"))
            if row.get("politician", "").casefold() == key and row.get("source_url") == final_url:
                lead["record_id"] = row["record_id"]
                lead["status"] = "Full transcript is already in the Civic Lens reader"
                INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
                return row
        except (OSError, KeyError, json.JSONDecodeError):
            continue

    raw_text = _plain(html_body.decode("utf-8", errors="replace"))
    title = lead.get("title", "")
    transcript_title = _is_full_text_lead(lead) or bool(
        re.search(r"transcript|full text|speech text|remarks as prepared", raw_text[:2000], re.I)
    )
    extracted = TranscriptParser().extract(
        html_body,
        transcript_title=transcript_title,
        politician=politician,
    )
    if not extracted or len(extracted[1].split()) < 120:
        lead["status"] = "No complete speech transcript could be extracted from this page"
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        raise ValueError("This page did not provide a complete transcript that Civic Lens could load.")

    extractor, text = extracted
    state = ""
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            state = next((row["state"] for row in csv.DictReader(handle)
                          if row["politician"].casefold() == key), "")
    except OSError:
        pass
    record_id = "live-speech-" + hashlib.sha1(f"{politician}|{final_url}".encode()).hexdigest()[:12]
    transcript_rel = f"live_cache/records/{record_id}.txt"
    txt_path = PROJECT_ROOT / "data" / "campaign_speeches" / transcript_rel
    html_path = RECORDS_ROOT / f"{record_id}.html"
    meta_path = RECORDS_ROOT / f"{record_id}.json"
    publication_date = lead.get("published") or _page_publication_date(html_body)
    date_value = publication_date or datetime.now(timezone.utc).date().isoformat()
    row = {
        "record_id": record_id,
        "politician": politician,
        "state": state,
        "date": date_value,
        "venue": title or f"Public speech by {politician}",
        "source_type": f"On-demand public transcript from {lead.get('publisher') or 'publisher'}",
        "source_category": "campaign",
        "source_url": final_url,
        "source_page_start": None,
        "source_page_end": None,
        "page_count": None,
        "transcript_path": transcript_rel,
        "transcript_status": (
            "on-demand v5 transcript; publisher publication date may differ from speech date; review transcript boundaries"
            if publication_date else
            "on-demand v5 transcript; retrieval date used because speech date is unknown; review transcript boundaries"
        ),
        "boundary_status": f"extracted from {extractor}; boundaries not independently checked",
    }
    try:
        RECORDS_ROOT.mkdir(parents=True, exist_ok=True)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(text + "\n", encoding="utf-8")
        html_path.write_bytes(html_body)
        meta_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as error:
        txt_path.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        raise RuntimeError("The transcript was found but could not be added to the local reader.") from error

    lead["source_url"] = final_url
    lead["record_id"] = record_id
    lead["status"] = "Full transcript loaded into the Civic Lens reader; review its boundaries"
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def discover_public_speeches(politician: str, *, force: bool = False) -> dict[str, Any]:
    """Search live public indexes, cache retrievable transcript text, and return leads."""
    RECORDS_ROOT.mkdir(parents=True, exist_ok=True)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    key = politician.casefold()
    index = _load_index()
    cached = index.get(key)
    if cached and cached.get("search_version") == SEARCH_VERSION and not force:
        try:
            searched = datetime.fromisoformat(cached["searched_at"])
            age_hours = (datetime.now(timezone.utc) - searched).total_seconds() / 3600
            if age_hours < CACHE_HOURS:
                return {**cached, "cache_status": "cached"}
        except (KeyError, TypeError, ValueError):
            pass

    queries = _queries(politician)
    rows: list[dict[str, str]] = []
    search_jobs = [(search, query) for query in queries for search in (_search_bing, _search_one)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        found_sets = pool.map(lambda job: job[0](job[1]), search_jobs)
        for (search, _), found in zip(search_jobs, found_sets):
            rows.extend(found)
    # Recheck previously surfaced source URLs after extraction rules change or
    # new search results arrive. This recovers transcript pages that an earlier
    # title-only filter classified as ordinary speech leads.
    if cached:
        searched_urls = {row.get("news_url") for row in rows}
        rows.extend(
            lead for lead in cached.get("leads", [])
            if lead.get("news_url") and lead.get("news_url") not in searched_urls
        )
    rows.sort(key=lambda row: urllib.parse.urlparse(row["news_url"]).netloc.casefold() == "news.google.com")
    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        deduped.setdefault(row["news_url"], row)
    # Search every mapped election cycle; keep all distinct results for the
    # transcript filter instead of dropping older campaigns after a small cap.
    leads = list(deduped.values())

    known_urls: set[str] = set()
    known_url_records: dict[str, str] = {}
    try:
        with (PROJECT_ROOT / "data" / "campaign_speeches" / "manifest.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("politician", "").casefold() == key and row.get("source_url"):
                    known_urls.add(row["source_url"])
                    known_url_records[row["source_url"]] = row.get("record_id", "")
    except OSError:
        pass
    for meta_path in RECORDS_ROOT.glob("*.json"):
        try:
            record = json.loads(meta_path.read_text(encoding="utf-8"))
            source_url = record.get("source_url")
            if record.get("politician", "").casefold() == key and source_url:
                known_urls.add(source_url)
                known_url_records[source_url] = record.get("record_id", "")
        except (OSError, json.JSONDecodeError):
            continue
    names = {}
    try:
        with ROSTER_PATH.open(encoding="utf-8", newline="") as handle:
            names = {row["politician"].casefold(): row["state"] for row in csv.DictReader(handle)}
    except OSError:
        pass
    state = names.get(key, "")
    candidate_leads = []
    fetchable = []
    invalid_urls: set[str] = set()
    for lead in leads:
        is_google_news = urllib.parse.urlparse(lead["news_url"]).netloc.casefold() == "news.google.com"
        if is_google_news and not _is_full_text_lead(lead):
            lead["status"] = "Google News lead; open to continue to the publisher page"
            lead["source_url"] = lead["news_url"]
            candidate_leads.append(lead)
            continue
        if not _is_full_text_lead(lead):
            lead["status"] = "speech/event lead; source title does not identify a transcript or full text"
            lead["source_url"] = lead["news_url"]
            invalid_urls.add(lead["news_url"])
            candidate_leads.append(lead)
            continue
        if lead["news_url"] in known_urls or lead.get("source_url") in known_urls:
            lead["record_id"] = known_url_records.get(lead["news_url"]) or known_url_records.get(lead.get("source_url", "")) or lead.get("record_id", "")
            lead["status"] = "already in the local speech collection"
            candidate_leads.append(lead)
            continue
        fetchable.append(lead)

    # Fetch every likely full-text result concurrently so their transcripts are
    # ready in the selected politician's corpus.
    def fetch_lead(lead: dict[str, str]) -> tuple[dict[str, str], str | None, bytes | None]:
        try:
            final_url, html_body = _fetch(lead["news_url"], timeout=7)
            return lead, final_url, html_body
        except Exception:
            return lead, None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        fetched = list(pool.map(fetch_lead, fetchable))

    new_count = 0
    seen_final_urls = set(known_urls)
    for lead, final_url, html_body in fetched:
        if final_url is None or html_body is None:
            lead["status"] = "source page could not be fetched; open the link to review"
            lead["source_url"] = lead["news_url"]
            candidate_leads.append(lead)
            continue
        if final_url in seen_final_urls:
            lead["record_id"] = known_url_records.get(final_url, lead.get("record_id", ""))
            lead["status"] = "already in the local speech collection"
            lead["source_url"] = final_url
            candidate_leads.append(lead)
            continue
        seen_final_urls.add(final_url)
        lead["source_url"] = final_url
        raw_text = _plain(html_body.decode("utf-8", errors="replace"))
        has_transcript_heading = bool(re.search(r"transcript|full text|\bspeech\b|remarks|\baddress\b", lead["title"] + " " + raw_text[:1500], re.I))
        extracted = TranscriptParser().extract(html_body, transcript_title=has_transcript_heading, politician=politician)
        if not extracted:
            lead["status"] = "speech/video lead; no full transcript text was extractable"
            invalid_urls.add(final_url)
            candidate_leads.append(lead)
            continue
        extractor, text = extracted
        if len(text.split()) < 120:
            lead["status"] = "source contains a short excerpt or article text, not a complete speech transcript"
            invalid_urls.add(final_url)
            candidate_leads.append(lead)
            continue
        content_key = f"{politician}|{final_url}"
        digest = hashlib.sha1(content_key.encode()).hexdigest()[:12]
        record_id = "live-speech-" + digest
        transcript_rel = f"live_cache/records/{record_id}.txt"
        txt_path = PROJECT_ROOT / "data" / "campaign_speeches" / transcript_rel
        html_path = RECORDS_ROOT / f"{record_id}.html"
        meta_path = RECORDS_ROOT / f"{record_id}.json"
        try:
            # Google News provides the article publication date, which may differ
            # from the date the speech was delivered. Store it as a source date
            # and disclose that distinction in the record metadata/UI.
            publication_date = lead["published"] or _page_publication_date(html_body)
            date_value = publication_date or datetime.now(timezone.utc).date().isoformat()
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            txt_path.write_text(text + "\n", encoding="utf-8")
            html_path.write_bytes(html_body)
            row = {
                "record_id": record_id,
                "politician": politician,
                "state": state,
                "date": date_value,
                "venue": lead["title"],
                "source_type": f"On-demand public transcript from {lead['publisher'] or 'publisher'}",
                "source_category": "campaign",
                "source_url": final_url,
                "source_page_start": None,
                "source_page_end": None,
                "page_count": None,
                "transcript_path": transcript_rel,
                "transcript_status": (
                    "on-demand v5 transcript; publisher publication date may differ from speech date; review transcript boundaries"
                    if publication_date else
                    "on-demand v5 transcript; retrieval date used because speech date is unknown; review transcript boundaries"
                ),
                "boundary_status": f"extracted from {extractor}; boundaries not independently checked",
            }
            meta_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            lead["status"] = "full speech text retrieved; review boundaries before treating as verified"
            lead["record_id"] = record_id
            new_count += 1
            known_urls.add(final_url)
        except OSError:
            lead["status"] = "transcript found but local cache could not be written"
        candidate_leads.append(lead)

    # Remove stale auto-extractions if the current source now proves to be an
    # article, video page, or partial excerpt. Curated files and CR records are
    # outside this flat-file cache and are never touched here.
    for meta_path in RECORDS_ROOT.glob("*.json"):
        try:
            row = json.loads(meta_path.read_text(encoding="utf-8"))
            if row.get("politician", "").casefold() != key or row.get("source_url") not in invalid_urls:
                continue
            transcript_path = PROJECT_ROOT / "data" / "campaign_speeches" / row["transcript_path"]
            transcript_path.unlink(missing_ok=True)
            meta_path.with_suffix(".html").unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        except (OSError, KeyError, json.JSONDecodeError):
            continue

    result = {
        "search_version": SEARCH_VERSION,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "queries_run": len(queries),
        "new_transcripts": new_count,
        "leads": candidate_leads,
        "cache_status": "searched live indexes",
    }
    index[key] = result
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _page_publication_date(raw: bytes) -> str:
    """Read common publication date metadata without treating retrieval time as speech time."""
    html = raw.decode("utf-8", errors="replace")
    tags = re.findall(r"(?is)<meta\b[^>]*>|<time\b[^>]*>", html)
    for tag in tags:
        attrs = {key.casefold(): unescape(value) for key, value in re.findall(r'''([\w:-]+)\s*=\s*["']([^"']*)["']''', tag)}
        kind = (attrs.get("property", "") + " " + attrs.get("name", "") + " " + attrs.get("itemprop", "")).casefold()
        value = attrs.get("content") or attrs.get("datetime") or ""
        if not value or not any(token in kind for token in ("published", "date", "created", "modified")):
            continue
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            continue
    return ""
