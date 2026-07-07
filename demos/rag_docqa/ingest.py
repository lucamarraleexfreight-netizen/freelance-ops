#!/usr/bin/env python3
"""
Ingest a folder of documents into a searchable index.

    python3 ingest.py                       # uses config.yaml
    python3 ingest.py --kb ./some/folder    # override knowledge base folder

Reads .md/.txt/.html (and .pdf if pypdf is installed), splits each into
overlapping chunks, and writes .vector_store/index.json. Swappable KB: point at
a different folder and re-run — the index rebuilds from scratch.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

SUPPORTED = {".md", ".txt", ".html", ".htm", ".pdf"}


def read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
        return re.sub(r"(?s)<[^>]+>", " ", raw)
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            print(f"  ! skipping {path.name}: pip install pypdf to ingest PDFs", file=sys.stderr)
            return ""
        reader = PdfReader(str(path))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages)
    return ""


def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """Split into ~chunk_size-char chunks on paragraph boundaries, with overlap."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for para in paras:
        if len(buf) + len(para) + 2 <= chunk_size or not buf:
            buf = f"{buf}\n\n{para}".strip()
        else:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{para}".strip()
    if buf:
        chunks.append(buf)
    return chunks


def build(kb_dir: str, chunk_size: int, overlap: int, backend: str, model_name: str) -> dict:
    kb = Path(kb_dir)
    if not kb.exists():
        print(f"knowledge base folder not found: {kb_dir}", file=sys.stderr)
        sys.exit(2)

    chunks = []
    files = sorted(p for p in kb.rglob("*") if p.suffix.lower() in SUPPORTED)
    if not files:
        print(f"no supported documents in {kb_dir} (looked for {sorted(SUPPORTED)})", file=sys.stderr)
        sys.exit(1)

    for path in files:
        text = read_file(path)
        if not text.strip():
            continue
        rel = str(path.relative_to(kb))
        for i, ch in enumerate(chunk_text(text, chunk_size, overlap)):
            chunks.append({
                "id": f"{rel}#{i}",
                "text": ch,
                "source": rel,
                "chunk_index": i,
            })

    index = {"backend": backend, "chunks": chunks}
    print(f"ingested {len(files)} file(s) -> {len(chunks)} chunk(s)")

    if backend == "embeddings":
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("backend=embeddings needs: pip install sentence-transformers", file=sys.stderr)
            sys.exit(2)
        print(f"embedding with {model_name} (first run downloads the model)...")
        model = SentenceTransformer(model_name)
        vectors = model.encode([c["text"] for c in chunks], normalize_embeddings=True)
        index["vectors"] = [v.tolist() for v in vectors]
        index["model_name"] = model_name

    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--kb", default=None, help="override knowledge base folder")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8")) if os.path.exists(args.config) else {}
    kb_dir = args.kb or cfg.get("knowledge_base", "knowledge_base")
    chunk_size = cfg.get("chunk_size", 900)
    overlap = cfg.get("chunk_overlap", 150)
    backend = cfg.get("retriever", {}).get("backend", "bm25")
    model_name = cfg.get("retriever", {}).get("model_name", "all-MiniLM-L6-v2")
    store = cfg.get("index_path", ".vector_store/index.json")

    index = build(kb_dir, chunk_size, overlap, backend, model_name)
    Path(store).parent.mkdir(parents=True, exist_ok=True)
    with open(store, "w", encoding="utf-8") as f:
        json.dump(index, f)
    print(f"wrote index -> {store}  (backend={backend})")


if __name__ == "__main__":
    main()
