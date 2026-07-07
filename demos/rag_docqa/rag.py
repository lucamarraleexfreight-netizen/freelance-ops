"""
Retrieve-then-generate with citations.

- Retrieval always runs (keyless): returns the top-k source chunks.
- Generation uses Anthropic to synthesize an answer that cites those chunks by
  [n]. If ANTHROPIC_API_KEY is missing, it does NOT fabricate an answer — it
  returns the retrieved passages and tells you to set the key. Honest by design.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from retriever import build_index


class RagEngine:
    def __init__(self, config_path: str = "config.yaml"):
        self.cfg = yaml.safe_load(open(config_path, encoding="utf-8")) if os.path.exists(config_path) else {}
        self.top_k = self.cfg.get("top_k", 4)
        self.model = self.cfg.get("generation", {}).get("model", "claude-haiku-4-5-20251001")
        self.max_tokens = self.cfg.get("generation", {}).get("max_tokens", 700)
        store = self.cfg.get("index_path", ".vector_store/index.json")
        if not Path(store).exists():
            raise RuntimeError(f"index not found at {store}. Run: python3 ingest.py")
        with open(store, encoding="utf-8") as f:
            self.index = build_index(json.load(f))

    def retrieve(self, question: str) -> list:
        return self.index.search(question, top_k=self.top_k)

    def answer(self, question: str) -> dict:
        hits = self.retrieve(question)
        if not hits:
            return {"answer": None, "generated": False,
                    "message": "No relevant passages found in the knowledge base.",
                    "sources": []}

        sources = [{"n": i + 1, "source": h["source"], "score": h["score"],
                    "excerpt": h["text"][:300]} for i, h in enumerate(hits)]

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "answer": None,
                "generated": False,
                "message": ("Retrieval works without a key. Set ANTHROPIC_API_KEY "
                            "to get a synthesized answer with citations. Meanwhile, "
                            "here are the most relevant passages:"),
                "sources": sources,
            }

        try:
            from anthropic import Anthropic
        except ImportError:
            return {"answer": None, "generated": False,
                    "message": "pip install anthropic to enable answer generation.",
                    "sources": sources}

        context = "\n\n".join(f"[{s['n']}] (from {s['source']})\n{hits[i]['text']}"
                              for i, s in enumerate(sources))
        prompt = (
            "Answer the question using ONLY the numbered context passages below. "
            "Cite the passages you use with their bracket numbers like [1], [2]. "
            "If the answer is not in the context, say so plainly — do not invent "
            "facts.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return {"answer": text, "generated": True, "message": "", "sources": sources}
