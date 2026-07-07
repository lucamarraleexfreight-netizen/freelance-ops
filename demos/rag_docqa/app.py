#!/usr/bin/env python3
"""
Minimal web UI for the RAG doc-Q&A bot.

    python3 app.py            # serves http://127.0.0.1:5000
    (ingest first: python3 ingest.py)

Endpoints:
    GET  /            -> the chat UI
    POST /ask         -> {question} -> {answer, generated, sources[]}
    GET  /health      -> index stats
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from datetime import date

from flask import Flask, jsonify, render_template, request

from rag import RagEngine

app = Flask(__name__)
_engine = None
_lock = threading.Lock()

# --- public-deploy guardrails (rate limit + daily budget + optional passcode) ---
# Protects the host's ANTHROPIC_API_KEY from being drained by random visitors.
RATE_LIMIT_PER_HOUR = int(os.environ.get("RAG_RATE_LIMIT_PER_HOUR", "10"))
DAILY_GENERATION_BUDGET = int(os.environ.get("RAG_DAILY_BUDGET", "50"))
PASSCODE = os.environ.get("RAG_PASSCODE", "")  # optional; if unset, budget+rate-limit alone gate generation

_hits_by_ip: dict[str, deque] = defaultdict(deque)
_budget_day = date.today()
_budget_used = 0


def engine() -> RagEngine:
    global _engine
    if _engine is None:
        _engine = RagEngine(os.environ.get("RAG_CONFIG", "config.yaml"))
    return _engine


def _rate_limited(ip: str) -> bool:
    now = time.time()
    with _lock:
        hits = _hits_by_ip[ip]
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_PER_HOUR:
            return True
        hits.append(now)
        return False


def _budget_exhausted() -> bool:
    global _budget_day, _budget_used
    with _lock:
        today = date.today()
        if today != _budget_day:
            _budget_day = today
            _budget_used = 0
        if _budget_used >= DAILY_GENERATION_BUDGET:
            return True
        _budget_used += 1
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    eng = engine()
    return jsonify({
        "chunks": len(eng.index.chunks),
        "backend": eng.cfg.get("retriever", {}).get("backend", "bm25"),
        "generation_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "empty question"}), 400

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    passcode_ok = (not PASSCODE) or data.get("passcode") == PASSCODE
    guard_blocked = _rate_limited(ip) or _budget_exhausted() or not passcode_ok

    try:
        eng = engine()
        if guard_blocked:
            # Fall back to retrieval-only instead of erroring or draining the key further.
            hits = eng.retrieve(question)
            sources = [{"n": i + 1, "source": h["source"], "score": h["score"],
                        "excerpt": h["text"][:300]} for i, h in enumerate(hits)]
            return jsonify({
                "answer": None,
                "generated": False,
                "message": "Rate limit / daily demo budget reached — showing retrieval-only results.",
                "sources": sources,
            })
        return jsonify(eng.answer(question))
    except Exception as e:  # never leak a stack trace to the browser
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"RAG doc-Q&A UI -> http://{host}:{port}  (Ctrl+C to stop)")
    app.run(host=host, port=port, debug=False)
