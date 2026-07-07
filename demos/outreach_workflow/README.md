# Demo #2 — Outreach Workflow (draft-and-approve)

Turns a list of leads into personalized outreach drafts, enriched from public
info, and parks them in an approval queue. **Nothing is ever sent
automatically** — a human reviews and approves, then sends. That human gate is
the design, not a limitation (see below).

Pipeline: `intake CSV → enrich → draft → queue → human approves → export .eml`

**What it demonstrates:** a real human-in-the-loop automation — the pattern
clients actually want for outreach, support triage, and content, where the AI
does the grunt work and a person owns the send.

---

## What it does

1. **Intake** — reads a CSV of leads (`company, contact_name, website, domain,
   category, email`). `email` blank = guess it; `domain` optional.
2. **Enrich** (keyless): fetches each site's homepage for its `<title>`, meta
   description, and social links; guesses the email from the contact name +
   domain using common patterns; optional DNS MX check. Any unreachable site
   degrades gracefully — it never crashes the run.
3. **Draft**: builds a short personalized email. Two modes:
   - **templated** (default, no API key) — deterministic mail-merge with a
     personalized opening pulled from the enrichment.
   - **llm** (optional) — Anthropic writes a tailored draft. Requires
     `ANTHROPIC_API_KEY`; if enabled without one it **stops with a clear error
     and does not fake a draft**.
4. **Queue**: writes drafts to a SQLite approval queue with status `pending`.
5. **Approve**: you review and approve/reject. Approved drafts export to
   `data/outbox/*.eml` — ready-to-send files you open in your mail client.

## Setup

```bash
cd demos/outreach_workflow
python3 -m pip install -r requirements.txt
```

## Run the demo (zero internet, no API key)

```bash
# Terminal 1 — local homepage fixture so enrichment works offline:
python3 fixture_site.py

# Terminal 2 — run the pipeline, then review:
python3 workflow.py --intake data/sample_intake.csv
python3 approval.py list
python3 approval.py show 1
python3 approval.py approve 1        # exports a ready-to-send .eml — does NOT send
python3 approval.py reject 3 "not a fit"
python3 approval.py review           # writes data/review.html to eyeball all drafts
```

Verified on build: 4 leads enriched (titles, descriptions, socials), emails
guessed against real domains (`dana@acmeplumbing.com`), personalized drafts
queued, approve/reject/export all working.

## Turning on LLM drafting (optional — needs a key)

Set `drafting.use_llm: true` in `config.yaml`, then provide `ANTHROPIC_API_KEY`
(see `.env.example`) and `pip install anthropic`. Without the key it stops and
tells you — by design. Pick your model in `config.model`.

## Repointing for a client

- Swap `data/sample_intake.csv` for their leads (same columns).
- Edit `sender` and the `drafting.template` / `subject` / `value_prop` in
  `config.yaml` to match the offer.
- Point enrichment at real sites (just real URLs in the `website` column) — the
  local fixture is only for the offline demo.

## Where a human IS the deliverable (important)

The **approval step is the product**, not a gap to automate away. Cold outreach
that auto-sends gets people blocklisted and burns domains. The value you sell is
"AI drafts, you approve in seconds, nothing embarrassing goes out." Say this
explicitly to clients — it's a feature.

Fully automated here: intake parsing, enrichment, email guessing, draft
generation, queueing, export. Human-owned: the approve/send decision, and
sanity-checking guessed emails before use.

> **Note:** guessed emails are *guesses*. Verify before sending (turn on the MX
> check, or use a verification service). The tool flags `email_source: guessed`
> so you know which ones to check.

## How to pitch it

> "I set up outreach automations that draft personalized emails from public info
> — but every message waits for your one-click approval before it sends, so
> nothing goes out that you didn't sign off on. Here's the pipeline running on
> sample leads and the drafts it produced."

Lead with the review queue and a sample draft. The approval gate is the
trust-builder — most 'automation' spooks clients because they picture spam going
out under their name.

## What to charge

Market (2026): automation freelancers get **$200–$1,500 per workflow build** and
**$1,000–$3,000/mo** for ongoing retainers; simple builds for clients run
$500–$2,500. ([CueBytes][1], [Intuz][2])

Your play:
- **First 1–2 gigs:** $200–$500 to build the intake→draft→approve flow for one
  offer. Priced to earn the review.
- **After reviews:** $600–$1,500 per build.
- **Retainer (the real money):** $500–$1,500/mo to run it weekly, refresh
  templates, and keep enrichment working. This recurs — lead with it.

[1]: https://cuebytes.com/blog/ai-automation-agency-cost
[2]: https://www.intuz.com/blog/cost-of-workflow-automation
