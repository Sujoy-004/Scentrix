"""Standalone Fragrantica scraper for external execution.

Features:
- 1-3 second randomized delay between requests
- Retry logic for transient HTTP/network failures
- Resumability via scraper_checkpoint.json
- Incremental append to data/fragrantica_raw.json (one record at a time)

This script is intended to run outside blocked environments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import signal
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


START_URL = "https://www.fragrantica.com/perfumes/"
CHECKPOINT_FILE = Path("scraper_checkpoint.json")
OUTPUT_FILE = Path("data/fragrantica_raw.json")


class FragranticaScraper:
    def __init__(
        self,
        target_records: int = 5000,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        request_timeout: int = 30,
    ):
        self.target_records = target_records
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_timeout = request_timeout
        self.stop_requested = False

        self.session = self._build_session()

        self.pending_listing_urls: deque[str] = deque()
        self.pending_fragrance_urls: deque[str] = deque()
        self.seen_listing_urls: set[str] = set()
        self.seen_fragrance_urls: set[str] = set()

        selfsaved_records = 0
        self.failures = 0

        self._register_signal_handlers()
        self._load_or_initialize_checkpoint()
        self._ensure_output_file()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    def _register_signal_handlers(self) -> None:
        def _handler(_sig: int, _frame: Any) -> None:
            self.stop_requested = True

        signal.signal(signal.SIGINT, _handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handler)

    def _ensure_output_file(self) -> None:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not OUTPUT_FILE.exists():
            OUTPUT_FILE.write_text("[]\n", encoding="utf-8")

    def _load_or_initialize_checkpoint(self) -> None:
        if not CHECKPOINT_FILE.exists():
            self.pending_listing_urls.append(START_URL)
            return

        try:
            data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
            self.pending_listing_urls = deque(data.get("pending_listing_urls", []))
            self.pending_fragrance_urls = deque(data.get("pending_fragrance_urls", []))
            self.seen_listing_urls = set(data.get("seen_listing_urls", []))
            self.seen_fragrance_urls = set(data.get("seen_fragrance_urls", []))
            self.saved_records = int(data.get("saved_records", 0))
            self.failures = int(data.get("failures", 0))

            if not self.pending_listing_urls and not self.pending_fragrance_urls:
                self.pending_listing_urls.append(START_URL)
        except Exception:
            # If checkpoint is corrupt, restart safely from start URL.
            self.pending_listing_urls = deque([START_URL])
            self.pending_fragrance_urls = deque()
            self.seen_listing_urls = set()
            self.seen_fragrance_urls = set()
            self.saved_records = 0
            self.failures = 0

    def _save_checkpoint(self) -> None:
        checkpoint = {
            "pending_listing_urls": list(self.pending_listing_urls),
            "pending_fragrance_urls": list(self.pending_fragrance_urls),
            "seen_listing_urls": list(self.seen_listing_urls),
            "seen_fragrance_urls": list(self.seen_fragrance_urls),
            "saved_records": self.saved_records,
            "failures": self.failures,
            "updated_at_epoch": int(time.time()),
        }
        CHECKPOINT_FILE.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")

    def _throttle(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _get(self, url: str) -> requests.Response | None:
        try:
            self._throttle()
            response = self.session.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                return response
            return None
        except requests.RequestException:
            return None

    def _append_record(self, record: dict[str, Any]) -> None:
        raw = json.dumps(record, ensure_ascii=False)

        with OUTPUT_FILE.open("r+b") as handle:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"[]\n")

            # Find trailing ']'
            handle.seek(0, 2)
            pos = handle.tell() - 1

            while pos >= 0:
                handle.seek(pos)
                ch = handle.read(1)
                if ch not in b" \t\r\n":
                    break
                pos -= 1

            if pos < 0:
                handle.seek(0)
                handle.truncate(0)
                handle.write(f"[\n{raw}\n]\n".encode("utf-8"))
                return

            handle.seek(pos)
            last = handle.read(1)
            if last != b"]":
                # Recover by rebuilding file as array from current valid JSON if possible.
                handle.seek(0)
                text = handle.read().decode("utf-8", errors="ignore").strip()
                try:
                    data = json.loads(text) if text else []
                    if not isinstance(data, list):
                        data = []
                except Exception:
                    data = []
                data.append(record)
                handle.seek(0)
                handle.truncate(0)
                handle.write((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
                return

            # Decide if existing array is empty.
            prev = pos - 1
            while prev >= 0:
                handle.seek(prev)
                ch = handle.read(1)
                if ch not in b" \t\r\n":
                    break
                prev -= 1

            is_empty = prev >= 0 and ch == b"["
            handle.seek(pos)

            if is_empty:
                handle.write(f"\n{raw}\n]\n".encode("utf-8"))
            else:
                handle.write(f",\n{raw}\n]\n".encode("utf-8"))

    @staticmethod
    def _extract_year(text: str) -> int | None:
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text)
        if not match:
            return None
        year = int(match.group(1))
        return year

    @staticmethod
    def _guess_gender(text: str) -> str:
        lowered = text.lower()
        if "for women and men" in lowered or "unisex" in lowered:
            return "Unisex"
        if "for women" in lowered or "female" in lowered:
            return "Female"
        if "for men" in lowered or "male" in lowered:
            return "Male"
        return "N/A"

    @staticmethod
    def _guess_concentration(text: str) -> str:
        lowered = text.lower()
        if "extrait de parfum" in lowered:
            return "Extrait de Parfum"
        if "eau de parfum" in lowered or " edp" in lowered:
            return "Eau de Parfum"
        if "eau de toilette" in lowered or " edt" in lowered:
            return "Eau de Toilette"
        if "eau de cologne" in lowered or " cologne" in lowered:
            return "Eau de Cologne"
        return "N/A"

    @staticmethod
    def _collect_unique_text(nodes: list[Any]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for node in nodes:
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    def _extract_notes_by_heading(self, soup: BeautifulSoup, heading_keywords: tuple[str, ...]) -> list[str]:
        heading = None

        for tag_name in ("h2", "h3", "h4", "strong", "b"):
            for candidate in soup.find_all(tag_name):
                text = candidate.get_text(" ", strip=True).lower()
                if any(keyword in text for keyword in heading_keywords):
                    heading = candidate
                    break
            if heading is not None:
                break

        if heading is None:
            return []

        collected_nodes = []
        cursor = heading
        for _ in range(30):
            cursor = cursor.find_next()
            if cursor is None:
                break

            if cursor.name in {"h2", "h3", "h4", "strong", "b"}:
                text = cursor.get_text(" ", strip=True).lower()
                if any(k in text for k in ("top notes", "middle notes", "heart notes", "base notes", "accord")):
                    if cursor is not heading:
                        break

            if cursor.name in {"a", "span", "li"}:
                cls = " ".join(cursor.get("class", []))
                if any(token in cls for token in ("note", "accord", "ingredient")) or cursor.name == "li":
                    collected_nodes.append(cursor)

        return self._collect_unique_text(collected_nodes)[:12]

    def _extract_accords(self, soup: BeautifulSoup) -> list[str]:
        selectors = [
            "div.accord-bar",
            "span.accord",
            "div.accord",
            "div.accords span",
        ]
        nodes = []
        for selector in selectors:
            nodes.extend(soup.select(selector))

        accords = self._collect_unique_text(nodes)
        if accords:
            return accords[:12]

        return self._extract_notes_by_heading(soup, ("main accords", "accords"))[:12]

    def _extract_record(self, url: str, html: str) -> dict[str, Any] | None:
        soup = BeautifulSoup(html, "lxml")

        name_node = soup.select_one("h1.fragranceName") or soup.select_one("h1")
        brand_node = soup.select_one("h3.brandName a") or soup.select_one("h3.brandName")

        name = name_node.get_text(" ", strip=True) if name_node else ""
        brand = brand_node.get_text(" ", strip=True) if brand_node else ""

        if not name or not brand:
            return None

        description_node = soup.select_one("div.description") or soup.select_one("meta[name='description']")
        if description_node is None:
            description = ""
        elif description_node.name == "meta":
            description = (description_node.get("content") or "").strip()
        else:
            description = description_node.get_text(" ", strip=True)
        description = description[:500]

        full_text = soup.get_text(" ", strip=True)
        year = self._extract_year(full_text)

        top_notes = self._extract_notes_by_heading(soup, ("top notes",))
        middle_notes = self._extract_notes_by_heading(soup, ("middle notes", "heart notes"))
        base_notes = self._extract_notes_by_heading(soup, ("base notes",))
        accords = self._extract_accords(soup)

        # Hard minimum to keep records meaningful for later cleaning.
        if not (top_notes or middle_notes or base_notes):
            return None

        record_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

        return {
            "id": f"frag_{record_id}",
            "name": name,
            "brand": brand,
            "year": year,
            "concentration": self._guess_concentration(full_text),
            "gender_label": self._guess_gender(full_text),
            "description": description,
            "top_notes": top_notes,
            "middle_notes": middle_notes,
            "base_notes": base_notes,
            "accords": accords,
            "url": url,
        }

    def _enqueue_listing_url(self, url: str) -> None:
        if url in self.seen_listing_urls:
            return
        if url in self.pending_listing_urls:
            return
        self.pending_listing_urls.append(url)

    def _enqueue_fragrance_url(self, url: str) -> None:
        if url in self.seen_fragrance_urls:
            return
        if url in self.pending_fragrance_urls:
            return
        self.pending_fragrance_urls.append(url)

    def _parse_listing(self, url: str, html: str) -> None:
        soup = BeautifulSoup(html, "lxml")

        link_candidates = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            if not href:
                continue

            absolute = urljoin(url, href)
            if "fragrantica.com/perfume" in absolute.lower() or "/perfumes/" in absolute:
                if re.search(r"/perfumes/.+\.html$", absolute):
                    link_candidates.append(absolute)

        for frag_url in link_candidates:
            self._enqueue_fragrance_url(frag_url)

        next_selectors = [
            "a.next[href]",
            "a[rel='next'][href]",
            "a.pagination__next[href]",
        ]
        next_url = None
        for selector in next_selectors:
            node = soup.select_one(selector)
            if node is not None:
                next_url = urljoin(url, node.get("href", ""))
                if next_url:
                    break

        if next_url:
            self._enqueue_listing_url(next_url)

    def run(self) -> int:
        checkpoint_interval = 10
        processed_since_checkpoint = 0

        while not self.stop_requested and self.saved_records < self.target_records:
            if self.pending_fragrance_urls:
                frag_url = self.pending_fragrance_urls.popleft()
                if frag_url in self.seen_fragrance_urls:
                    continue

                self.seen_fragrance_urls.add(frag_url)
                response = self._get(frag_url)
                if response is None:
                    self.failures += 1
                    processed_since_checkpoint += 1
                    if processed_since_checkpoint >= checkpoint_interval:
                        self._save_checkpoint()
                        processed_since_checkpoint = 0
                    continue

                record = self._extract_record(frag_url, response.text)
                if record is not None:
                    self._append_record(record)
                    self.saved_records += 1

                processed_since_checkpoint += 1
                if processed_since_checkpoint >= checkpoint_interval:
                    self._save_checkpoint()
                    processed_since_checkpoint = 0

                continue

            if self.pending_listing_urls:
                listing_url = self.pending_listing_urls.popleft()
                if listing_url in self.seen_listing_urls:
                    continue

                self.seen_listing_urls.add(listing_url)
                response = self._get(listing_url)
                if response is None:
                    self.failures += 1
                    processed_since_checkpoint += 1
                    if processed_since_checkpoint >= checkpoint_interval:
                        self._save_checkpoint()
                        processed_since_checkpoint = 0
                    continue

                self._parse_listing(listing_url, response.text)
                processed_since_checkpoint += 1
                if processed_since_checkpoint >= checkpoint_interval:
                    self._save_checkpoint()
                    processed_since_checkpoint = 0
                continue

            # No more work currently queued.
            break

        self._save_checkpoint()

        print(f"saved_records={self.saved_records}")
        print(f"target_records={self.target_records}")
        print(f"failures={self.failures}")
        print(f"output_file={OUTPUT_FILE}")
        print(f"checkpoint_file={CHECKPOINT_FILE}")

        if self.saved_records >= self.target_records:
            print("status=target_reached")
            return 0

        if self.stop_requested:
            print("status=stopped_and_checkpointed")
            return 0

        print("status=finished_without_target")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resumable Fragrantica scraper")
    parser.add_argument("--target-records", type=int, default=5000)
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=3.0)
    parser.add_argument("--request-timeout", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_delay <= 0 or args.max_delay <= 0 or args.max_delay < args.min_delay:
        print("Invalid delay values. Require: 0 < min_delay <= max_delay", file=sys.stderr)
        return 2

    scraper = FragranticaScraper(
        target_records=args.target_records,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        request_timeout=args.request_timeout,
    )
    return scraper.run()


if __name__ == "__main__":
    raise SystemExit(main())
