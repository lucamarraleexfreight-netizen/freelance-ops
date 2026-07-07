#!/usr/bin/env python3
"""
Config-driven lead scraper.

Point it at any list/directory-style source via a YAML config: it paginates,
extracts structured records per CSS selectors, dedupes (in-run + persistent
across runs), rate-limits politely, retries with backoff, and writes CSV
(always) plus Google Sheets (optional, see sheets_export.py).

Usage:
    python3 scraper.py                        # uses config.yaml
    python3 scraper.py --config config.books.yaml
    python3 scraper.py --max-pages 3 --dry-run

Nothing here is site-specific: swap config.yaml to repoint at a new source.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml
from bs4 import BeautifulSoup

log = logging.getLogger("lead_scraper")


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class RunStats:
    pages_fetched: int = 0
    rows_seen: int = 0
    new_rows: int = 0
    duplicate_rows: int = 0
    page_errors: int = 0
    errors: list = field(default_factory=list)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ("source", "list", "fields", "output"):
        if key not in cfg:
            raise ValueError(f"config missing required top-level key: '{key}'")
    return cfg


# --------------------------------------------------------------------------- #
# HTTP session with retries + polite rate limiting
# --------------------------------------------------------------------------- #
class PoliteSession:
    def __init__(self, http_cfg: dict):
        self.timeout = http_cfg.get("timeout", 15)
        self.retries = http_cfg.get("retries", 3)
        self.backoff_factor = http_cfg.get("backoff_factor", 1.5)
        self.rate_limit = http_cfg.get("rate_limit_seconds", 1.0)
        self.jitter = http_cfg.get("jitter_seconds", 0.5)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": http_cfg.get(
                "user_agent",
                "Mozilla/5.0 (compatible; LeadScraper/1.0; +https://example.com/bot)",
            )
        })
        self._last_request_ts = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.rate_limit - elapsed
        if wait > 0:
            time.sleep(wait)
        if self.jitter:
            time.sleep(random.uniform(0, self.jitter))
        self._last_request_ts = time.monotonic()

    def get(self, url: str) -> requests.Response:
        """GET with manual exponential backoff on transient failures."""
        last_exc = None
        for attempt in range(1, self.retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                resp.raise_for_status()
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding
                return resp
            except (requests.RequestException,) as e:
                last_exc = e
                if attempt < self.retries:
                    sleep = self.backoff_factor ** attempt
                    log.warning("  fetch failed (%s), retry %d/%d in %.1fs: %s",
                                type(e).__name__, attempt, self.retries, sleep, url)
                    time.sleep(sleep)
        raise last_exc


# --------------------------------------------------------------------------- #
# robots.txt
# --------------------------------------------------------------------------- #
def robots_allows(url: str, user_agent: str) -> bool:
    try:
        parts = urlparse(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # If robots.txt is unreachable/unparseable, default to allowed but warn.
        log.warning("  could not read robots.txt for %s; proceeding", url)
        return True


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def extract_field(card, spec: dict, base_url: str) -> str:
    selector = spec["selector"]
    attr = spec.get("attr", "text")
    el = card.select_one(selector)
    if el is None:
        return ""
    if attr == "text":
        return _clean(el.get_text())
    value = el.get(attr, "")
    if isinstance(value, (list, tuple)):        # e.g. the 'class' attribute
        value = " ".join(value)
    if attr in ("href", "src") and value:
        value = urljoin(base_url, value)        # resolve relative links
    return _clean(value)


def parse_page(html: str, base_url: str, list_cfg: dict, fields_cfg: dict) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(list_cfg["row_selector"])
    rows = []
    for card in cards:
        row = {name: extract_field(card, spec, base_url) for name, spec in fields_cfg.items()}
        if any(row.values()):  # skip fully-empty rows
            rows.append(row)
    return rows


def find_next_url(html: str, base_url: str, pagination: dict) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(pagination["next_selector"])
    if el and el.get("href"):
        return urljoin(base_url, el["href"])
    return None


# --------------------------------------------------------------------------- #
# Dedupe state (persistent across runs)
# --------------------------------------------------------------------------- #
class SeenStore:
    def __init__(self, keys: list[str], state_file: str | None, persist: bool):
        self.keys = keys
        self.state_file = state_file
        self.persist = persist
        self._seen: set[str] = set()
        if persist and state_file and Path(state_file).exists():
            try:
                self._seen = set(json.loads(Path(state_file).read_text()))
            except Exception:
                log.warning("could not read dedupe state at %s; starting fresh", state_file)

    def _key(self, row: dict) -> str:
        return "||".join(_clean(str(row.get(k, ""))).lower() for k in self.keys)

    def is_new(self, row: dict) -> bool:
        k = self._key(row)
        if k in self._seen:
            return False
        self._seen.add(k)
        return True

    def save(self):
        if self.persist and self.state_file:
            Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
            Path(self.state_file).write_text(json.dumps(sorted(self._seen)))


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_csv(rows: list[dict], fieldnames: list[str], path: str, mode: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    file_exists = Path(path).exists()
    open_mode = "a" if mode == "append" and file_exists else "w"
    with open(path, open_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if open_mode == "w" or not file_exists:
            writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------- #
# Pagination drivers
# --------------------------------------------------------------------------- #
def iter_page_urls(pagination: dict, start_url: str):
    """Yield page URLs for query_param / page_path modes (next_link handled inline)."""
    mode = pagination.get("mode", "query_param")
    max_pages = pagination.get("max_pages", 20)
    if mode == "query_param":
        param = pagination.get("param", "page")
        start = pagination.get("start", 1)
        sep = "&" if "?" in start_url and not start_url.endswith(("?", "&")) else ""
        base = start_url
        # Strip any existing page param from the template start_url.
        for i in range(start, start + max_pages):
            if "{page}" in base:
                yield base.replace("{page}", str(i))
            elif f"{param}=" in base:
                import re
                yield re.sub(rf"{param}=\d+", f"{param}={i}", base)
            else:
                joiner = "?" if "?" not in base else "&"
                yield f"{base}{joiner}{param}={i}"
    elif mode == "page_path":
        template = pagination["template"]  # e.g. ".../page-{page}.html"
        start = pagination.get("start", 1)
        for i in range(start, start + max_pages):
            yield template.replace("{page}", str(i))
    else:
        raise ValueError(f"iter_page_urls does not handle mode '{mode}'")


# --------------------------------------------------------------------------- #
# Main scrape
# --------------------------------------------------------------------------- #
def scrape(cfg: dict, max_pages_override: int | None, dry_run: bool) -> tuple[list[dict], RunStats]:
    stats = RunStats()
    http = PoliteSession(cfg.get("http", {}))
    ua = http.session.headers["User-Agent"]
    respect_robots = cfg.get("http", {}).get("respect_robots", True)

    pagination = cfg.get("pagination", {"mode": "query_param"})
    if max_pages_override is not None:
        pagination["max_pages"] = max_pages_override
    stop_on_empty = pagination.get("stop_on_empty", True)
    mode = pagination.get("mode", "query_param")

    dedupe_cfg = cfg.get("dedupe", {})
    seen = SeenStore(
        keys=dedupe_cfg.get("keys", list(cfg["fields"].keys())),
        state_file=dedupe_cfg.get("state_file"),
        persist=dedupe_cfg.get("persist_across_runs", False),
    )

    collected: list[dict] = []
    start_url = cfg["source"]["start_url"]

    if respect_robots and not robots_allows(start_url, ua):
        log.error("robots.txt disallows scraping %s for UA '%s'. Aborting.", start_url, ua)
        stats.errors.append("blocked by robots.txt")
        return collected, stats

    def handle_html(html: str, page_url: str) -> int:
        rows = parse_page(html, page_url, cfg["list"], cfg["fields"])
        stats.rows_seen += len(rows)
        new_here = 0
        for row in rows:
            if seen.is_new(row):
                collected.append(row)
                stats.new_rows += 1
                new_here += 1
            else:
                stats.duplicate_rows += 1
        return new_here if rows else -1  # -1 signals an empty page

    if mode == "next_link":
        url = start_url
        max_pages = pagination.get("max_pages", 20)
        for _ in range(max_pages):
            log.info("fetching %s", url)
            try:
                resp = http.get(url)
            except Exception as e:
                stats.page_errors += 1
                stats.errors.append(f"{url}: {e}")
                log.error("  giving up on page after retries: %s", e)
                break
            stats.pages_fetched += 1
            got = handle_html(resp.text, url)
            if stop_on_empty and got == -1:
                log.info("  empty page, stopping.")
                break
            nxt = find_next_url(resp.text, url, pagination)
            if not nxt or nxt == url:
                log.info("  no next link, stopping.")
                break
            url = nxt
    else:
        for url in iter_page_urls(pagination, start_url):
            log.info("fetching %s", url)
            try:
                resp = http.get(url)
            except Exception as e:
                stats.page_errors += 1
                stats.errors.append(f"{url}: {e}")
                log.error("  giving up on page after retries: %s", e)
                continue
            stats.pages_fetched += 1
            got = handle_html(resp.text, url)
            if stop_on_empty and got == -1:
                log.info("  empty page, stopping.")
                break

    if not dry_run:
        seen.save()
    return collected, stats


def main():
    ap = argparse.ArgumentParser(description="Config-driven lead scraper")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--max-pages", type=int, default=None, help="override pagination.max_pages")
    ap.add_argument("--dry-run", action="store_true", help="scrape but do not write output or state")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    cfg_path = args.config
    if not Path(cfg_path).exists():
        log.error("config not found: %s", cfg_path)
        sys.exit(2)
    cfg = load_config(cfg_path)

    t0 = time.monotonic()
    rows, stats = scrape(cfg, args.max_pages, args.dry_run)
    elapsed = time.monotonic() - t0

    fieldnames = list(cfg["fields"].keys())
    out = cfg["output"]
    csv_path = out["csv_path"]

    if not args.dry_run and rows:
        write_csv(rows, fieldnames, csv_path, out.get("mode", "overwrite"))

    # Optional Google Sheets export (kept in a separate module; requires creds).
    gs = out.get("google_sheets", {})
    if gs.get("enabled") and not args.dry_run and rows:
        try:
            from sheets_export import export_to_sheets
            export_to_sheets(rows, fieldnames, gs)
            log.info("Exported %d rows to Google Sheet %s", len(rows), gs.get("spreadsheet_id"))
        except Exception as e:
            log.error("Google Sheets export failed: %s", e)
            stats.errors.append(f"sheets: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"  Source:        {cfg['source'].get('name', cfg['source']['start_url'])}")
    print(f"  Pages fetched: {stats.pages_fetched}")
    print(f"  Rows seen:     {stats.rows_seen}")
    print(f"  New (written): {stats.new_rows}")
    print(f"  Duplicates:    {stats.duplicate_rows}")
    print(f"  Page errors:   {stats.page_errors}")
    print(f"  Elapsed:       {elapsed:.1f}s")
    if not args.dry_run and rows:
        print(f"  CSV:           {csv_path}")
    if args.dry_run:
        print("  (dry-run: nothing written)")
    print("=" * 60)
    if stats.errors:
        print("  Errors:")
        for e in stats.errors[:10]:
            print(f"    - {e}")
    # Non-zero exit if every page failed (useful for cron/monitoring).
    if stats.pages_fetched == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
