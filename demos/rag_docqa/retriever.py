"""
Retrieval backends for the RAG demo.

Default: BM25 — a classic lexical ranking function, pure standard library. No
model downloads, fully offline, deterministic. Good enough for doc-Q&A and easy
to inspect.

Optional: sentence-transformers embeddings for semantic search (set
retriever.backend: embeddings in config). Requires `pip install
sentence-transformers`, which downloads a model on first use (needs internet
once). The interface is identical, so rag.py doesn't care which is active.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = set(
    "a an and are as at be by for from has have in is it its of on or that the "
    "to was were will with this these those you your our we they he she them".split()
)


def tokenize(text: str) -> list:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


class BM25Index:
    """BM25 Okapi over a list of chunk dicts: {id, text, source, chunk_index}."""

    def __init__(self, chunks: list, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(c["text"]) for c in chunks]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.tf = [Counter(t) for t in self.doc_tokens]
        df = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                df[term] += 1
        n = len(chunks)
        # BM25 idf with +1 smoothing so it's always positive.
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, top_k: int = 4) -> list:
        q_terms = tokenize(query)
        scored = []
        for i, chunk in enumerate(self.chunks):
            score = 0.0
            dl = self.doc_len[i] or 1
            for term in q_terms:
                if term not in self.tf[i]:
                    continue
                f = self.tf[i][term]
                idf = self.idf.get(term, 0.0)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                score += idf * (f * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": round(s, 4), **c} for s, c in scored[:top_k]]


class EmbeddingIndex:
    """Cosine similarity over sentence-transformer embeddings (optional)."""

    def __init__(self, chunks: list, vectors, model_name: str):
        self.chunks = chunks
        self.vectors = vectors  # list[list[float]], normalized
        self.model_name = model_name
        self._model = None

    def _embed(self, text: str):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        import numpy as np
        v = self._model.encode([text], normalize_embeddings=True)[0]
        return np.asarray(v, dtype="float32")

    def search(self, query: str, top_k: int = 4) -> list:
        import numpy as np
        q = self._embed(query)
        mat = np.asarray(self.vectors, dtype="float32")
        sims = mat @ q
        idx = np.argsort(-sims)[:top_k]
        return [{"score": round(float(sims[i]), 4), **self.chunks[i]} for i in idx]


def build_index(index_data: dict):
    """Reconstruct the right retriever from a loaded index file."""
    backend = index_data.get("backend", "bm25")
    chunks = index_data["chunks"]
    if backend == "embeddings":
        return EmbeddingIndex(chunks, index_data["vectors"], index_data["model_name"])
    return BM25Index(chunks)
