"""Fetch explicitly seeded campaign-speech sources without generating text."""
from __future__ import annotations
import argparse, csv, hashlib, html, re, ssl, certifi
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path("data/campaign_speeches")
FIELDS = ["record_id", "politician", "state", "date", "venue", "source_type", "source_url", "transcript_path", "transcript_status", "notes"]

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def visible_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

class SpeechBlockParser(HTMLParser):
    """Read transcript paragraphs from known archive article containers."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.rich_active: list[tuple[int, list[str]]] = []
        self.rich_candidates: list[list[str]] = []
        self.quote_depth = 0
        self.quote_parts: list[str] = []
        self.storytext_depth: int | None = None
        self.storytext_paragraphs: list[str] = []
        self.storytext_candidates: list[list[str]] = []
        self.current_storytext_paragraph: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        self.stack.append(tag)
        if tag == "div" and attrs_dict.get("id") == "storytext":
            self.storytext_depth = len(self.stack)
            self.storytext_paragraphs = []
        if tag == "div" and "blog-text-rich-text" in (attrs_dict.get("class") or "").split():
            self.rich_active.append((len(self.stack), []))
        if tag == "p" and self.storytext_depth is not None:
            self.current_storytext_paragraph = []
        if tag == "br" and self.storytext_depth is not None and self.current_storytext_paragraph is not None:
            self.current_storytext_paragraph.append("\n")
        if tag == "blockquote":
            self.quote_depth += 1
        if tag in {"p", "br"}:
            for _, parts in self.rich_active:
                parts.append("\n")
            if self.quote_depth:
                self.quote_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self.storytext_depth is not None and self.current_storytext_paragraph is not None:
            paragraph = re.sub(r"\s+", " ", "".join(self.current_storytext_paragraph)).strip()
            if paragraph:
                self.storytext_paragraphs.append(paragraph)
            self.current_storytext_paragraph = None
        if tag == "blockquote" and self.quote_depth:
            self.quote_depth -= 1
        if tag == "div":
            if self.storytext_depth == len(self.stack):
                self.storytext_candidates.append(self.storytext_paragraphs)
                self.storytext_depth = None
                self.current_storytext_paragraph = None
            ending = [item for item in self.rich_active if item[0] == len(self.stack)]
            self.rich_candidates.extend(parts for _, parts in ending)
            self.rich_active = [item for item in self.rich_active if item[0] != len(self.stack)]
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data: str) -> None:
        if self.storytext_depth is not None and self.current_storytext_paragraph is not None:
            self.current_storytext_paragraph.append(data)
        for _, parts in self.rich_active:
            parts.append(data)
        if self.quote_depth:
            self.quote_parts.append(data)

    def transcript(self, raw: bytes) -> tuple[str, str]:
        self.feed(raw.decode("utf-8", errors="replace"))
        rich_texts = ["".join(parts) for parts in self.rich_candidates]
        rich_texts.extend("".join(parts) for _, parts in self.rich_active)
        rich_texts.sort(key=len, reverse=True)
        choices = [("Rev transcript body", value) for value in rich_texts]
        choices.append(("source transcript blockquote", "".join(self.quote_parts)))
        for paragraphs in self.storytext_candidates:
            for index, paragraph in enumerate(paragraphs):
                if re.match(r"Transcript of .+? speech as (?:prepared for delivery|delivered)", paragraph, re.I):
                    body = "\n\n".join(paragraphs[index + 1:])
                    if len(body) >= 800:
                        return body, "NPR storytext transcript paragraphs"
        for source, value in choices:
            text = re.sub(r"Copyright Disclaimer\s+Under Title 17.*?infringing\.?", "", value, flags=re.I | re.S)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
            if len(text) >= 800:
                return text, source
        return visible_text(raw), "visible page text (review required)"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-file", type=Path, required=True)
    args = parser.parse_args()
    if not args.seed_file.is_file():
        raise SystemExit(f"Missing seed file: {args.seed_file}")
    capture_dir = ROOT / "captures"; capture_dir.mkdir(parents=True, exist_ok=True)
    report = ROOT / "review_queue.csv"; rows = []
    with args.seed_file.open(encoding="utf-8", newline="") as handle:
        for seed in csv.DictReader(handle):
            url = seed["source_url"].strip()
            record_id = seed.get("record_id") or f"campaign-{slug(seed['politician'])}-{seed['date']}-{hashlib.sha1(url.encode()).hexdigest()[:8]}"
            if urlparse(url).scheme not in {"http", "https"}:
                rows.append({**seed, "record_id": record_id, "transcript_path": "", "transcript_status": "rejected", "notes": "invalid URL"}); continue
            try:
                request = Request(url, headers={"User-Agent": "MGT409-campaign-speech-collector/1.0"})
                with urlopen(request, timeout=30, context=ssl.create_default_context(cafile=certifi.where())) as response:
                    body = response.read(); final_url = response.geturl()
                path = capture_dir / f"{slug(record_id)}.html"; path.write_bytes(body)
                transcript, method = SpeechBlockParser().transcript(body)
                headings = list(re.finditer(r"(?m)^([A-Z][A-Za-z .'-]+)\s+\(\d{2}:\d{2}\):\s*", transcript))
                matching_heading = next((i for i, match in enumerate(headings) if seed["politician"].casefold() in match.group(1).casefold()), None)
                if matching_heading is not None and len(headings) > 1:
                    start = headings[matching_heading].start()
                    end = headings[matching_heading + 1].start() if matching_heading + 1 < len(headings) else len(transcript)
                    transcript = transcript[start:end].strip()
                    method += "; selected the named speaker from a joint transcript"
                surname = seed["politician"].split()[-1].upper()
                label = re.search(rf"(?m)^{re.escape(surname)}:\s*", transcript)
                if label and re.match(r"(?m)^[A-Z][A-Z ]+:\s*", transcript[:label.start()]):
                    transcript = transcript[label.end():].strip()
                    method += "; selected the named speaker from a joint transcript"
                text_path = capture_dir / f"{slug(record_id)}.txt"; text_path.write_text(transcript + "\n", encoding="utf-8")
                rows.append({**seed, "record_id": record_id, "source_url": final_url, "transcript_path": str(text_path.relative_to(ROOT)), "transcript_status": "needs human verification", "notes": f"{method}; {len(transcript)} characters; not imported"})
            except Exception as exc:
                rows.append({**seed, "record_id": record_id, "transcript_path": "", "transcript_status": "fetch failed", "notes": str(exc)})
    with report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    print(f"Fetched {sum(r['transcript_status'] == 'needs human verification' for r in rows)} source captures; review queue: {report}")

if __name__ == "__main__": main()
