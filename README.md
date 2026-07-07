# freelance-ops

Operational base for a one-person, AI-leveraged freelancing operation. Three
runnable demos that double as portfolio proof and resellable, config-driven
templates — plus the profile, proposals, and gig tracker to go land the work.

Everything here runs. Where something needs an API key or a service I wasn't
given, it says so and stops instead of faking success (see the flags below).

## Layout

```
freelance-ops/
├─ demos/               three runnable builds (portfolio + engine)
│  ├─ lead_scraper/     #1 config-driven scraper -> deduped CSV / Sheets
│  ├─ outreach_workflow/#2 intake -> enrich -> draft -> human approval
│  └─ rag_docqa/        #3 doc-Q&A bot with citations + web UI
├─ templates/           new_client.py: spin a client build from a demo
├─ gig-tracker/         SQLite CLI: gig, client, status, pay, deliverable
├─ proposals/           parameterized template + 3 filled examples
└─ profile/             Upwork profile + 3 niche variants
```

## Quickstart (each demo is standalone)

```bash
# #1 Lead scraper — runs offline against a bundled fixture
cd demos/lead_scraper && pip install -r requirements.txt
python3 fixture/serve_fixture.py            # terminal 1
python3 scraper.py                          # terminal 2 -> output/leads.csv

# #2 Outreach workflow — offline, no key needed
cd demos/outreach_workflow && pip install -r requirements.txt
python3 fixture_site.py                     # terminal 1
python3 workflow.py --intake data/sample_intake.csv   # terminal 2
python3 approval.py review                  # eyeball the drafts

# #3 RAG doc-Q&A — retrieval offline; generation needs a key
cd demos/rag_docqa && pip install -r requirements.txt
python3 ingest.py && python3 app.py         # http://127.0.0.1:5000
```

## What's fully automated vs. where a human is required

| Demo | Fully automated | Human is the deliverable |
|------|-----------------|--------------------------|
| #1 Scraper | fetch, paginate, extract, dedupe, CSV/Sheets | confirming a source's TOS; first-time field mapping |
| #2 Outreach | intake, enrich, email-guess, draft, queue | **approving/sending** (by design); verifying guessed emails |
| #3 Doc-Q&A | ingest, chunk, retrieve, cite, serve UI | one query with your key to confirm generation; chunk tuning |

## What needs a key / service (and what runs without one)

- **Runs with zero keys:** all of #1 (CSV), all of #2 (templated drafts), and #3
  retrieval + citations + UI.
- **Needs `ANTHROPIC_API_KEY`:** #2 LLM-drafting mode (optional) and #3 answer
  generation. Both stop with a clear message if the key is missing — no faked
  output. Model is set to `claude-haiku-4-5-20251001` in config; change it to
  your preferred model.
- **Needs a Google service account:** #1 Google Sheets export (optional; CSV
  needs nothing). Setup steps are in `demos/lead_scraper/sheets_export.py`.
- **Needs `pip install` extras only:** #3 `embeddings` backend
  (sentence-transformers, downloads a model once) and `.pdf` ingest (pypdf).

## Using the business side

- **profile/** — paste the base profile or one of the three niche variants into
  Upwork. Fill `{GITHUB_URL}` with this repo's public URL.
- **proposals/** — adapt `proposal_template.md`; the three examples show it
  filled per niche. Keep them 4–6 sentences.
- **gig-tracker/** — log every lead/gig: `python3 tracker.py add ...`.

## Ground rules baked in

Real working code, no stubs. Config-driven so each demo repoints per client.
Honest failure modes over fake success. Each demo has its own README with setup,
how to pitch it, and what to charge.

> Verified on build in a Linux sandbox (Python 3.10). You're on Windows with
> `python3`; the code is standard-library-first and cross-platform. Two
> environment notes: SQLite writes to local disk (not a synced/network folder),
> and the demos that reach the internet (live-site scraping, LLM generation) need
> your machine's normal connectivity — the build sandbox had none, so those
> exact paths are the ones flagged for your one-step QA.
