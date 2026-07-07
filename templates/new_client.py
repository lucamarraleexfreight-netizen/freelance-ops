#!/usr/bin/env python3
"""
Spin up a per-client build from one of the verified demos.

The demos in ../demos are already config-driven, so a "template" here just means:
copy the verified engine into a client-named folder and drop in a fresh config
skeleton for you to fill. That keeps one source of truth (the demo) instead of a
drifting duplicate.

    python3 new_client.py scraper  --client acme
    python3 new_client.py outreach --client acme
    python3 new_client.py rag      --client acme

Creates:  templates/clients/<client>_<demo>/   (copied engine + CONFIG_TODO.md)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMOS = HERE.parent / "demos"

DEMO_MAP = {
    "scraper": "lead_scraper",
    "outreach": "outreach_workflow",
    "rag": "rag_docqa",
}

# Files/dirs not worth copying into a client build (regenerated or demo-only).
SKIP = {"__pycache__", "output", ".vector_store", "data", "fixture",
        "fixture_site.py", "review.html"}

TODO = """# Client build: {client} — {demo}

Copied from the verified demo `demos/{demo_dir}`. To adapt:

{steps}

When it runs clean for {client}, log it in ../../gig-tracker:
    python3 tracker.py add --gig "{demo} for {client}" --client "{client}" --status active
"""

STEPS = {
    "lead_scraper": (
        "1. Edit config.yaml: source.start_url, pagination, list.row_selector, fields, dedupe.keys.\n"
        "2. CONFIRM the source's TOS permits scraping (your call, not the tool's).\n"
        "3. Run: python3 scraper.py   ->  output/leads.csv\n"
        "4. Optional Google Sheets: see sheets_export.py setup."
    ),
    "outreach_workflow": (
        "1. Replace data/sample_intake.csv with the client's leads (same columns).\n"
        "2. Edit config.yaml: sender, drafting.template/subject/value_prop.\n"
        "3. Run: python3 workflow.py --intake data/<their>.csv, then approval.py review.\n"
        "4. Approval stays human — that's the selling point."
    ),
    "rag_docqa": (
        "1. Drop the client's docs into knowledge_base/ (or --kb a folder).\n"
        "2. Run: python3 ingest.py  then  python3 app.py\n"
        "3. Set ANTHROPIC_API_KEY for generated answers; tune chunk_size if needed."
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("demo", choices=DEMO_MAP.keys())
    ap.add_argument("--client", required=True)
    args = ap.parse_args()

    demo_dir = DEMO_MAP[args.demo]
    src = DEMOS / demo_dir
    if not src.exists():
        print(f"demo not found: {src}", file=sys.stderr)
        sys.exit(2)

    client_slug = "".join(c if c.isalnum() else "_" for c in args.client.lower()).strip("_")
    dest = HERE / "clients" / f"{client_slug}_{args.demo}"
    if dest.exists():
        print(f"already exists: {dest}", file=sys.stderr)
        sys.exit(1)

    dest.mkdir(parents=True)
    copied = []
    for item in src.iterdir():
        if item.name in SKIP:
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name,
                            ignore=shutil.ignore_patterns(*SKIP))
        else:
            shutil.copy2(item, dest / item.name)
        copied.append(item.name)

    (dest / "CONFIG_TODO.md").write_text(
        TODO.format(client=args.client, demo=args.demo, demo_dir=demo_dir,
                    steps=STEPS[demo_dir]),
        encoding="utf-8",
    )
    print(f"Created {dest}")
    print(f"  copied: {', '.join(sorted(copied))}")
    print(f"  next:   open {dest / 'CONFIG_TODO.md'}")


if __name__ == "__main__":
    main()
