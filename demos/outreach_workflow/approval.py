"""
Human-in-the-loop approval queue (SQLite).

The workflow writes drafts here with status 'pending'. NOTHING is ever sent
automatically. A human reviews, then approves/rejects. Approved drafts are
exported to data/outbox/ as ready-to-send .eml files that YOU send from your
mail client (or wire to SMTP yourself, deliberately, later).

CLI:
    python3 approval.py list                  # show all drafts + status
    python3 approval.py show <id>             # full draft
    python3 approval.py approve <id>          # mark approved + export .eml
    python3 approval.py reject <id> [reason]  # mark rejected
    python3 approval.py review                # write review.html to eyeball
    python3 approval.py export                # (re)export all approved to outbox
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    company     TEXT,
    contact     TEXT,
    to_email    TEXT,
    subject     TEXT,
    body        TEXT,
    draft_mode  TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending|approved|rejected
    note        TEXT,
    enrichment  TEXT
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def add_draft(conn, lead: dict, draft: dict):
    conn.execute(
        "INSERT INTO drafts (created_at, company, contact, to_email, subject, body, "
        "draft_mode, status, enrichment) VALUES (?,?,?,?,?,?,?, 'pending', ?)",
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            lead.get("company", ""),
            lead.get("contact_name", ""),
            lead.get("email", ""),
            draft.get("subject", ""),
            draft.get("body", ""),
            draft.get("draft_mode", ""),
            json.dumps({k: lead.get(k) for k in
                        ("site_title", "site_description", "socials",
                         "guessed_emails", "email_source", "email_mx_ok")}),
        ),
    )
    conn.commit()


def _export_one(row: sqlite3.Row, outbox_dir: str) -> str:
    Path(outbox_dir).mkdir(parents=True, exist_ok=True)
    msg = EmailMessage()
    msg["To"] = row["to_email"] or "UNKNOWN@example.com"
    msg["Subject"] = row["subject"] or ""
    msg.set_content(row["body"] or "")
    safe = "".join(c for c in (row["company"] or "lead") if c.isalnum() or c in "-_")
    path = os.path.join(outbox_dir, f"{row['id']:04d}_{safe}.eml")
    with open(path, "wb") as f:
        f.write(bytes(msg))
    return path


def cmd_list(conn):
    rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
    if not rows:
        print("(queue empty — run workflow.py first)")
        return
    for r in rows:
        print(f"[{r['id']:>3}] {r['status']:<9} {r['company']:<28} -> {r['to_email']:<38} {r['subject']}")


def cmd_show(conn, draft_id):
    r = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    if not r:
        print(f"no draft {draft_id}")
        return
    print(f"id:       {r['id']}")
    print(f"status:   {r['status']}")
    print(f"company:  {r['company']}  ({r['contact']})")
    print(f"to:       {r['to_email']}")
    print(f"subject:  {r['subject']}")
    print(f"mode:     {r['draft_mode']}")
    print(f"enrich:   {r['enrichment']}")
    print("-" * 60)
    print(r["body"])
    print("-" * 60)


def cmd_approve(conn, draft_id, outbox_dir):
    r = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    if not r:
        print(f"no draft {draft_id}")
        return
    conn.execute("UPDATE drafts SET status='approved' WHERE id=?", (draft_id,))
    conn.commit()
    r = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    path = _export_one(r, outbox_dir)
    print(f"approved #{draft_id}. Exported ready-to-send: {path}")
    print("(This does NOT send. Open the .eml in your mail client and send it yourself.)")


def cmd_reject(conn, draft_id, reason=""):
    conn.execute("UPDATE drafts SET status='rejected', note=? WHERE id=?", (reason, draft_id))
    conn.commit()
    print(f"rejected #{draft_id}. {reason}")


def cmd_export(conn, outbox_dir):
    rows = conn.execute("SELECT * FROM drafts WHERE status='approved' ORDER BY id").fetchall()
    for r in rows:
        print("exported", _export_one(r, outbox_dir))
    print(f"{len(rows)} approved draft(s) in {outbox_dir}")


def cmd_review(conn, out_html="data/review.html"):
    rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
    cards = []
    for r in rows:
        body_html = (r["body"] or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
        cards.append(f"""
        <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:12px 0">
          <div style="color:#888;font-size:12px">#{r['id']} · {r['status'].upper()} · {r['draft_mode']}</div>
          <div><b>{r['company']}</b> — {r['contact']} &lt;{r['to_email']}&gt;</div>
          <div style="margin:6px 0"><b>Subject:</b> {r['subject']}</div>
          <div style="background:#fafafa;padding:10px;border-radius:6px">{body_html}</div>
        </div>""")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Outreach review</title></head>
    <body style="font-family:system-ui,sans-serif;max-width:760px;margin:24px auto">
    <h1>Outreach drafts — review</h1>
    <p>{len(rows)} draft(s). Approve/reject from the CLI: <code>python3 approval.py approve &lt;id&gt;</code></p>
    {''.join(cards)}</body></html>"""
    Path(out_html).parent.mkdir(parents=True, exist_ok=True)
    Path(out_html).write_text(html, encoding="utf-8")
    print(f"wrote {out_html} ({len(rows)} drafts)")


def main():
    # Minimal config read for db/outbox paths.
    import yaml
    cfg_path = os.environ.get("OUTREACH_CONFIG", "config.yaml")
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}
    q = cfg.get("queue", {})
    db_path = q.get("db_path", "data/queue.db")
    outbox_dir = q.get("outbox_dir", "data/outbox")

    if len(sys.argv) < 2:
        print(__doc__)
        return
    conn = connect(db_path)
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list(conn)
    elif cmd == "show" and len(sys.argv) > 2:
        cmd_show(conn, int(sys.argv[2]))
    elif cmd == "approve" and len(sys.argv) > 2:
        cmd_approve(conn, int(sys.argv[2]), outbox_dir)
    elif cmd == "reject" and len(sys.argv) > 2:
        cmd_reject(conn, int(sys.argv[2]), " ".join(sys.argv[3:]))
    elif cmd == "export":
        cmd_export(conn, outbox_dir)
    elif cmd == "review":
        cmd_review(conn)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
