#!/usr/bin/env python3
"""
Dead-simple gig tracker (SQLite + CLI).

    python3 tracker.py add --gig "Scraper for Acme" --client Acme --pay 350 --status lead
    python3 tracker.py list                     # all gigs
    python3 tracker.py list --status active     # filter
    python3 tracker.py update 3 --status active --pay 500
    python3 tracker.py done 3 --deliverable "leads.csv + tool"
    python3 tracker.py summary                  # counts + pipeline/earned $
    python3 tracker.py export                   # write gigs.md (eyeball/share)

Statuses (free-form, but these are the intended flow):
    lead -> proposed -> active -> delivered -> paid   (or: lost)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

DB = Path(__file__).with_name("gigs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS gigs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    gig         TEXT NOT NULL,
    client      TEXT,
    status      TEXT NOT NULL DEFAULT 'lead',
    pay         REAL DEFAULT 0,
    deliverable TEXT,
    notes       TEXT,
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
);
"""

EARNED = {"paid"}
PIPELINE = {"lead", "proposed", "active", "delivered"}


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(SCHEMA)
    return c


def _today() -> str:
    return date.today().isoformat()


def add(c, a):
    c.execute(
        "INSERT INTO gigs (gig, client, status, pay, deliverable, notes, created, updated) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (a.gig, a.client, a.status, a.pay or 0, a.deliverable, a.notes, _today(), _today()),
    )
    c.commit()
    print(f"added gig #{c.execute('SELECT last_insert_rowid()').fetchone()[0]}: {a.gig}")


def update(c, a):
    row = c.execute("SELECT * FROM gigs WHERE id=?", (a.id,)).fetchone()
    if not row:
        print(f"no gig #{a.id}", file=sys.stderr)
        sys.exit(1)
    fields, vals = [], []
    for name in ("gig", "client", "status", "pay", "deliverable", "notes"):
        v = getattr(a, name, None)
        if v is not None:
            fields.append(f"{name}=?")
            vals.append(v)
    if not fields:
        print("nothing to update (pass --status/--pay/--deliverable/…)")
        return
    fields.append("updated=?")
    vals.append(_today())
    vals.append(a.id)
    c.execute(f"UPDATE gigs SET {', '.join(fields)} WHERE id=?", vals)
    c.commit()
    print(f"updated gig #{a.id}")


def done(c, a):
    c.execute("UPDATE gigs SET status='delivered', deliverable=COALESCE(?, deliverable), updated=? WHERE id=?",
              (a.deliverable, _today(), a.id))
    c.commit()
    print(f"gig #{a.id} marked delivered")


def _rows(c, status=None):
    if status:
        return c.execute("SELECT * FROM gigs WHERE status=? ORDER BY id", (status,)).fetchall()
    return c.execute("SELECT * FROM gigs ORDER BY id").fetchall()


def list_gigs(c, a):
    rows = _rows(c, a.status)
    if not rows:
        print("(no gigs)")
        return
    print(f"{'ID':>3}  {'STATUS':<10} {'CLIENT':<16} {'PAY':>8}  GIG")
    print("-" * 68)
    for r in rows:
        print(f"{r['id']:>3}  {r['status']:<10} {(r['client'] or '-'):<16} {r['pay']:>8.0f}  {r['gig']}")


def summary(c, a):
    rows = _rows(c)
    earned = sum(r["pay"] for r in rows if r["status"] in EARNED)
    pipeline = sum(r["pay"] for r in rows if r["status"] in PIPELINE)
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    print(f"gigs: {len(rows)}")
    print("by status: " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    print(f"pipeline $ (unpaid): {pipeline:,.0f}")
    print(f"earned $ (paid):     {earned:,.0f}")


def export_md(c, a):
    rows = _rows(c)
    out = Path(__file__).with_name("gigs.md")
    lines = ["# Gig tracker", "", f"_Exported {_today()}_", "",
             "| ID | Status | Client | Pay | Gig | Deliverable |",
             "|----|--------|--------|-----|-----|-------------|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['status']} | {r['client'] or ''} | "
                     f"{r['pay']:.0f} | {r['gig']} | {r['deliverable'] or ''} |")
    earned = sum(r["pay"] for r in rows if r["status"] in EARNED)
    pipeline = sum(r["pay"] for r in rows if r["status"] in PIPELINE)
    lines += ["", f"**Pipeline (unpaid):** ${pipeline:,.0f}  ", f"**Earned (paid):** ${earned:,.0f}"]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def build_parser():
    p = argparse.ArgumentParser(description="Dead-simple gig tracker")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add"); a.set_defaults(fn=add)
    a.add_argument("--gig", required=True)
    a.add_argument("--client")
    a.add_argument("--status", default="lead")
    a.add_argument("--pay", type=float, default=0)
    a.add_argument("--deliverable")
    a.add_argument("--notes")

    u = sub.add_parser("update"); u.set_defaults(fn=update)
    u.add_argument("id", type=int)
    u.add_argument("--gig"); u.add_argument("--client"); u.add_argument("--status")
    u.add_argument("--pay", type=float); u.add_argument("--deliverable"); u.add_argument("--notes")

    d = sub.add_parser("done"); d.set_defaults(fn=done)
    d.add_argument("id", type=int); d.add_argument("--deliverable")

    l = sub.add_parser("list"); l.set_defaults(fn=list_gigs); l.add_argument("--status")
    sub.add_parser("summary").set_defaults(fn=summary)
    sub.add_parser("export").set_defaults(fn=export_md)
    return p


def main():
    args = build_parser().parse_args()
    c = conn()
    args.fn(c, args)


if __name__ == "__main__":
    main()
