# Demo #1 — Config-Driven Lead Scraper

Scrapes a paginated list/directory source into clean, **deduplicated** structured
data (CSV always; Google Sheets optional). Everything site-specific lives in a
YAML config, so the same engine repoints at a new client source by editing one
file — no code changes.

**What it demonstrates to a prospect:** pagination handling, polite rate-limiting
with jitter, retry-with-backoff on transient failures, composite-key dedupe
(in-run *and* persistent across runs), robots.txt respect, and graceful
per-page failure recovery instead of crashing.

---

## What it does

- Walks pages via one of three strategies: follow a "next" link (`next_link`),
  increment `?page=N` (`query_param`), or fill a `{page}` URL template (`page_path`).
- Extracts one record per element matching `list.row_selector`, pulling each
  field by CSS selector + attribute (`text`, `href`, `class`, …). Relative links
  are resolved to absolute URLs automatically.
- Drops duplicates on a composite key you choose (e.g. `name` + `address`).
  With `persist_across_runs: true` it remembers what it has seen, so repeat runs
  surface only *new* leads — useful for scheduled incremental pulls.
- Writes `output/leads.csv` and prints a run summary (pages, new, dupes, errors).

## Setup

```bash
cd demos/lead_scraper
python3 -m pip install -r requirements.txt
```

## Run the demo (zero internet required)

The default config targets a self-contained fixture that ships in this repo — a
fake business directory served on localhost. It runs anywhere, offline.

```bash
# Terminal 1 — start the demo directory:
python3 fixture/serve_fixture.py

# Terminal 2 — scrape it:
python3 scraper.py
```

Expected: 5 pages, 48 rows seen, **3 duplicates dropped, 45 clean records** in
`output/leads.csv`. (Verified on build.)

## Run against a real site

`config.books.yaml` targets `books.toscrape.com` — a public sandbox built for
scraping practice. This needs internet (works on your machine):

```bash
python3 scraper.py --config config.books.yaml
```

Handy flags: `--max-pages 3` (cap for a quick test), `--dry-run` (parse without
writing), `-v` (verbose).

## Repointing at a client source

Copy `config.yaml`, then change:
- `source.start_url` — first page of the client's list.
- `pagination` — pick the mode that matches their paging; set `next_selector`
  or the URL pattern.
- `list.row_selector` — the element wrapping one record (inspect the page).
- `fields` — one entry per column you want, with its selector + attribute.
- `dedupe.keys` — the fields that make a record unique.

That's the whole job for most single-source scrapes.

## Google Sheets output (optional — needs credentials)

CSV works with zero setup. Sheets export is **off by default** and requires a
Google service account — it will not fake success. To enable it, follow the
SETUP steps at the top of `sheets_export.py`, drop `service_account.json` in
this folder, share the target sheet with the service account's email, then set
`output.google_sheets.enabled: true` and the `spreadsheet_id` in your config.

## Where a human is still required

- **TOS/legality of a client's source.** This engine respects robots.txt, but
  *you* confirm a given site permits scraping before pointing it there. That
  judgment is the operator's job, not the tool's.
- **Field-mapping the first time** on a new site (inspecting selectors) is a
  5-minute human step; after that it's fully automated and re-runnable.

## How to pitch it

> "I build config-driven scrapers that turn a messy directory into a clean,
> deduplicated spreadsheet — with pagination, rate-limiting, and retries handled
> so it doesn't break on page 40. Here's a run against a live site and the CSV
> it produced. I can repoint it at your source and hand you the data plus the
> tool, or run it on a schedule."

Lead with the CSV output and the live-site run. The selling point isn't "I can
scrape" — it's "I ship something reusable that doesn't fall over."

## What to charge

Market rates (2026): simple single-site scrapes run **$500–$2,000** fixed;
median scraping rate is ~$30/hr, top-rated $50–100+/hr. ([Upwork][1], [pricing guide][2])

Your play while killing the zero-review problem:
- **First 1–2 gigs:** $150–$350 fixed for a single-source scraper → clean CSV +
  the tool. Priced to win the review, not to profit. Say so to yourself, not the
  client.
- **After 3–5 reviews:** $600–$1,500 fixed per source.
- **Recurring refresh/monitoring:** $100–$300/mo retainer (scheduled runs +
  fixing breakage when the site changes). This is where the real money is —
  maintenance is $100–$1,000/mo at market.

[1]: https://www.upwork.com/hire/web-scrapers/cost/
[2]: https://tendem.ai/blog/web-scraping-cost-pricing-guide
