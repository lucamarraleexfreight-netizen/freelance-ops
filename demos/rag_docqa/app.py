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

from flask import Flask, jsonify, render_template, request

from rag import RagEngine

app = Flask(__name__)
_engine = None


def engine() -> RagEngine:
    global _engine
    if _engine is None:
        _engine = RagEngine(os.environ.get("RAG_CONFIG", "config.yaml"))
    return _engine


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
    try:
        return jsonify(engine().answer(question))
    except Exception as e:  # never leak a stack trace to the browser
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"RAG doc-Q&A UI -> http://127.0.0.1:{port}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=port, debug=False)
