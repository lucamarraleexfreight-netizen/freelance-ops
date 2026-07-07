# Demo #3 — RAG Doc-Q&A Bot (with citations)

Point it at a folder of documents, ask questions in a clean web UI, get answers
grounded in those docs **with citations back to the source**. Swap the folder,
re-ingest, and it answers about a different knowledge base.

**What it demonstrates:** the "chat with your docs" build clients ask for —
ingestion, chunking, retrieval, cited answers, and a usable UI — done honestly:
it cites sources and refuses to answer from outside the documents.

---

## How it works

```
folder of docs ──► ingest.py ──► index ──► retriever (BM25) ──► top-k chunks
                                                                     │
   web UI (app.py) ◄── answer + citations ◄── Anthropic synthesis ◄──┘
```

- **Retrieval is keyless and offline.** The default retriever is **BM25** (pure
  standard library) — no model downloads, deterministic, fully runnable with
  zero API keys. An optional `embeddings` backend (sentence-transformers) gives
  semantic search if you want it.
- **Generation uses Anthropic.** It synthesizes an answer from the retrieved
  chunks and cites them `[1] [2]`. **Without `ANTHROPIC_API_KEY` it does not
  invent an answer** — it returns the retrieved passages and tells you to add
  the key. That honesty is the point of a doc-Q&A tool.

## Setup

```bash
cd demos/rag_docqa
python3 -m pip install -r requirements.txt   # just Flask + PyYAML for the default path
```

## Run the demo

```bash
python3 ingest.py        # builds the index from knowledge_base/ (ships with sample docs)
python3 app.py           # serves http://127.0.0.1:5000
```

Open the UI and click an example, or ask your own. Verified on build: 4 sample
docs → 7 chunks; "How is data encrypted?" retrieves `security.md` (top score),
"refund policy" retrieves `pricing.md`, "uptime SLA" retrieves `support.md` —
each with a source citation.

## Turning on generated answers (needs a key)

```bash
pip install anthropic
# Windows PowerShell:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python3 app.py
```

Now `/ask` returns a synthesized answer citing `[n]` the passages it used. Model
is set in `config.yaml` (`generation.model`).

> **Not verified on my build:** the generated-answer path requires your key,
> which I don't have, and the build environment has no outbound internet — so I
> verified ingestion, retrieval, citations, and the full web UI, but **you** run
> one query with your key to confirm generation. Everything it needs is wired;
> this is the one human-verified step.

## Swappable knowledge base

```bash
python3 ingest.py --kb "C:\path\to\client\docs"
python3 app.py
```

Supports `.md`, `.txt`, `.html` out of the box; `.pdf` if you `pip install
pypdf`. Re-running `ingest.py` rebuilds the index from scratch.

## Semantic (embeddings) retrieval — optional

Set `retriever.backend: embeddings` in `config.yaml`, `pip install
sentence-transformers`, and re-ingest. First run downloads a small model
(~90 MB, needs internet once). Better at synonyms/paraphrases than BM25; slower
to build. BM25 is the default because it runs anywhere with nothing to download.

## Where a human is required

- **Generation quality check** with your key (above) — one query.
- **Chunk-size tuning** per corpus: dense PDFs or transcripts may want a
  different `chunk_size`/`overlap`. Sensible defaults ship; tuning is a
  10-minute human step per new client corpus.

Fully automated: ingestion, chunking, indexing, retrieval, citation, serving.

## How to pitch it

> "I build 'chat with your documents' bots that answer from *your* content and
> cite the source for every claim — so your team can trust the answer and click
> through to verify. Here's it running on a sample knowledge base; I'll point it
> at yours and stand up the same UI."

Lead with the citations. The reason internal doc-bots fail is hallucination;
"every answer cites its source, and it won't answer from outside your docs" is
the differentiator.

## What to charge

Market (2026): a basic RAG over a small knowledge base runs **$4,000–$10,000**;
intermediate pipelines $8,000–$18,000. Data prep is 30–50% of the work.
([Stratagem][1], [Heeya][2])

Your play:
- **First proof gig:** $800–$2,000 for a single-KB bot (this exact build,
  repointed) — priced to earn the review, well under market.
- **After reviews:** $3,000–$8,000 for a scoped internal doc-bot.
- **Retainer:** $300–$1,000/mo to keep it ingesting new docs + monitor answer
  quality. Hosting/model costs are pass-through on top.

[1]: https://www.stratagem-systems.com/blog/rag-implementation-cost-roi-analysis
[2]: https://heeya.fr/en/blog/how-much-does-an-ai-chatbot-cost-2026
