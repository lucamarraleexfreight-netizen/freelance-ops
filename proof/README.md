# Proof artifacts

Real outputs from live runs of all three demos on 2026-07-06. No fabricated content.

- **`leads.csv`** — first 25 rows of a live scrape of books.toscrape.com (100 rows total, 5 pages, 0 errors). Proves demo #1 works against a real live site, not just the bundled offline fixture.
- **`review.html`** — the human-approval queue from demo #2, showing 4 LLM-generated (`claude-haiku-4-5-20251001`) personalized outreach drafts. Proves the draft→review pipeline runs end-to-end with real Anthropic API calls.
- **`0001_AcmePlumbing.eml`** — one approved draft exported as a ready-to-send `.eml` file. Proves the approval step produces a real send-ready artifact — and that nothing auto-sends (this file just sits on disk until you open it in a mail client).
- **`rag_answer.md`** — one real question ("How is data encrypted?") answered by demo #3 with a generated response citing its source document (`security.md`), plus retrieval scores for two other chunks that were retrieved but unused. Proves the "chat with your docs, get real citations" claim.

## Screenshots / recordings

No reliable screenshot/browser-automation tool was available in this session, so no
images were captured. To finish the portfolio proof, record a ~60-second Loom
(https://www.loom.com) of each demo — takes ~5 minutes total:

1. **lead_scraper**: terminal running `python3 scraper.py --config config.books.yaml`, then open `output/books.csv` to show the rows.
2. **outreach_workflow**: open `data/review.html` in a browser, scroll through the 4 drafts, then run `python3 approval.py approve 2` in a terminal to show the `.eml` export message.
3. **rag_docqa**: run `python3 app.py`, open `http://127.0.0.1:5000`, type "How is data encrypted?" into the UI, and show the answer with its `[1]` citation.

Drop the resulting Loom links into `profile/upwork_profile.md` and this file once recorded.
