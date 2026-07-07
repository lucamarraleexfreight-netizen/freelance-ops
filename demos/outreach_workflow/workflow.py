#!/usr/bin/env python3
"""
Outreach workflow: intake (CSV) -> enrich -> draft -> queue for human approval.

    python3 workflow.py --intake data/sample_intake.csv

Never sends. It only fills an approval queue (SQLite). Review + approve with
approval.py. See README.md.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

import yaml

from enrich import enrich_lead
from draft import make_draft
from approval import connect, add_draft

log = logging.getLogger("outreach")


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        log.error("config not found: %s", path)
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_intake(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--intake", default="data/sample_intake.csv")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")

    cfg = load_config(args.config)
    leads = read_intake(args.intake)
    if not leads:
        log.error("no rows in %s", args.intake)
        sys.exit(1)

    conn = connect(cfg.get("queue", {}).get("db_path", "data/queue.db"))

    made, failed = 0, 0
    for lead in leads:
        company = lead.get("company", "?")
        try:
            enriched = enrich_lead(lead, cfg)
            draft = make_draft(enriched, cfg)
            add_draft(conn, enriched, draft)
            made += 1
            note = enriched.get("enrich_note") or "ok"
            log.info("queued: %-28s email=%s (%s) [%s]",
                    company, enriched.get("email", "-"),
                    enriched.get("email_source", "-"), note)
        except Exception as e:
            failed += 1
            log.error("FAILED on %s: %s", company, e)
            # If LLM drafting is misconfigured, stop loudly rather than churn.
            if "ANTHROPIC_API_KEY" in str(e):
                log.error("Stopping: fix the key or set drafting.use_llm: false.")
                sys.exit(3)

    print("\n" + "=" * 56)
    print(f"  Queued for approval: {made}")
    print(f"  Failed:              {failed}")
    print(f"  DB:                  {cfg.get('queue', {}).get('db_path', 'data/queue.db')}")
    print("  Next: python3 approval.py list   (nothing has been sent)")
    print("=" * 56)


if __name__ == "__main__":
    main()
