# GO_LIVE — the only things left for you

Everything buildable is built, verified, and shipped:
- All 3 demos run live: https://github.com/lucamarraleexfreight-netizen/freelance-ops
- Proof artifacts: `proof/` (real CSV, real drafts, real cited Q&A)
- Live clickable demo: https://freelance-ops-rag-docqa.onrender.com

**Be honest with yourself about the first move: the goal is 3–5 reviews at
under-market prices, not maximizing your first invoice.** Price to win the
review; raise rates after.

## 1. Create + ID-verify an Upwork account

Go to upwork.com → sign up as a freelancer → complete profile → submit ID
verification. **This step alone can take Upwork a day or more** to clear —
start it first, today, and do the rest of this checklist while it's pending.

## 2. Paste your profile

Use `profile/upwork_profile.md`. Pick **one** variant to lead with based on
what you want to bid on first (you can only have one Upwork title/overview):

- **Title:** pick from `BASE POSITIONING`, `VARIANT A` (scraping), `VARIANT B`
  (outreach automation), or `VARIANT C` (RAG/doc-Q&A) in that file.
- **Overview:** paste the matching variant's overview paragraph verbatim.
- **Skills:** paste the matching variant's skill list into Upwork's skill tags.
- Recommended starting hourly: **$25–$40** (per the note at the bottom of
  `profile/upwork_profile.md`) — low enough to clear client filters, but you'll
  actually win on fixed-price gigs below.

## 3. Add portfolio items

In Upwork's Portfolio section, add these three entries:

1. **GitHub repo** — https://github.com/lucamarraleexfreight-netizen/freelance-ops
   *"Three working automation/AI builds: scraper, outreach pipeline, doc-Q&A bot — all open source, all runnable."*
2. **Live RAG demo** — https://freelance-ops-rag-docqa.onrender.com
   *"Try it live: ask a question, get a cited answer. This is the same bot I'll point at your docs."*
3. **Proof artifacts** — link or screenshot from `proof/` (leads.csv, review.html, rag_answer.md)
   *"Real output from a live scrape, a real LLM-drafted outreach email, and a real cited Q&A answer — not mockups."*

If you haven't yet, record the three ~60-second Looms per `proof/README.md`
and add those as portfolio video entries too — video converts better than
static screenshots on Upwork.

## 4. Use `proposals/` for your first 5 bids

- Template: `proposals/proposal_template.md` — keep it 4–6 sentences, adapt to
  the specific job post, don't send it verbatim.
- Filled examples per niche: `proposals/examples/example_scraper.md`,
  `example_outreach.md`, `example_rag.md`.
- **Pricing to quote** (pulled from each demo's README "What to charge" section):

  | Demo | First 1–2 gigs (win the review) | After 3–5 reviews |
  |---|---|---|
  | Lead scraper | $150–$350 fixed | $600–$1,500 fixed; $100–$300/mo retainer |
  | Outreach workflow | $200–$500 fixed | $600–$1,500 fixed; $500–$1,500/mo retainer |
  | RAG doc-Q&A | $800–$2,000 fixed | $3,000–$8,000 scoped; $300–$1,000/mo retainer |

  Quote the **low end** of the "first gigs" column until you have reviews.
  Retainers are where the real recurring money is — mention them once you
  have proof, not on gig #1.

## 5. Log every bid and gig

```bash
cd gig-tracker
python3 tracker.py add --client "..." --gig "..." --demo scraper --status bid --rate 250
```

Track status (`bid` → `won`/`lost` → `delivered` → `paid`) for every
application, not just the ones you win — it's the only way to see your actual
win rate and fix your pitch if it's low.

## What's live right now

- All 3 demos verified running with your real Anthropic key (Phase 1).
- `proof/` has real, unfaked artifacts from all 3 (Phase 2).
- Public GitHub repo pushed, all placeholders filled (Phase 3).
- RAG demo deployed publicly with rate-limit + daily-budget key protection —
  **you still need to set a hard monthly spend cap** in the Anthropic console
  (console.anthropic.com/settings/billing) — I can't do that for you (Phase 4).
- This checklist (Phase 5).

## What you still owe

1. Create/verify the Upwork account (step 1 above) — start this now, it's the
   longest pole.
2. Set the Anthropic spend cap.
3. Record the 3 Looms (optional but recommended — see `proof/README.md`).
4. Paste your profile, add portfolio items, start bidding.

## Single highest-leverage next action

**Start the Upwork ID verification right now** — it's the only step with a
multi-day lag, and everything else on this list you can finish in an
afternoon while it processes.
