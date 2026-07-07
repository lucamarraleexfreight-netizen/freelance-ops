# RAG Doc-Q&A — sample query with citations

**Backend:** BM25 retrieval (keyless) + Anthropic `claude-haiku-4-5-20251001` generation
**Knowledge base:** 4 sample docs → 7 chunks (ingested via `ingest.py`)

## Question
> How is data encrypted?

## Generated answer
Based on the context provided:

Data is encrypted in two ways [1]:

1. **In transit**: All data is encrypted using TLS 1.2 or higher.
2. **At rest**: Data is encrypted with AES-256.

Additionally, encryption keys are rotated every 90 days and managed through a hardware security module (HSM) [1].

## Sources cited
- **[1] security.md** (score 3.66) — "All data is encrypted in transit using TLS 1.2 or higher. Data at rest is encrypted with AES-256. Encryption keys are rotated every 90 days and managed through a hardware security module (HSM)."
- [2] onboarding.md (score 1.29) — retrieved but not needed for this answer
- [3] support.md (score 0.70) — retrieved but not needed for this answer

`generated: true` — confirms this is a live Anthropic-generated answer, not the keyless retrieval-only fallback.
