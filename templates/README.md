# templates/ — per-client builds

Each demo in `../demos` is already config-driven, so it *is* the reusable
template. Rather than keep a second copy that drifts out of sync, `new_client.py`
copies the verified engine into a client-named folder with a fresh config
skeleton and a `CONFIG_TODO.md` checklist.

```bash
cd templates
python3 new_client.py scraper  --client acme      # lead scraper for "acme"
python3 new_client.py outreach --client acme      # outreach workflow
python3 new_client.py rag      --client acme      # doc-Q&A bot
```

Result: `templates/clients/acme_scraper/` — the runnable engine plus
`CONFIG_TODO.md` telling you exactly what to edit for that client. The demo's
fixtures, sample data, and build outputs are left behind; you point the config at
the client's real source.

`clients/` is where your active client builds live; keep secrets (`.env`,
`service_account.json`) out of version control (the root `.gitignore` already
covers them).

## Why not a separate parameterized copy of each engine?

Because it would rot. One verified engine + a copy-and-configure step means a
fix to the demo is a fix everywhere. If a specific client needs engine changes,
their copy is theirs to diverge — the demo stays the clean reference.
