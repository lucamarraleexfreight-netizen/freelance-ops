# gig-tracker

One SQLite file, one CLI. Tracks gig, client, status, pay, deliverable.

```bash
cd gig-tracker
python3 tracker.py add --gig "Scraper for Acme" --client Acme --pay 350 --status lead
python3 tracker.py list
python3 tracker.py list --status active
python3 tracker.py update 1 --status active --pay 500
python3 tracker.py done 1 --deliverable "leads.csv + repointed tool"
python3 tracker.py summary          # counts + pipeline $ vs earned $
python3 tracker.py export           # writes gigs.md to eyeball or share
```

Intended status flow: `lead → proposed → active → delivered → paid` (or `lost`).
Statuses are free-form strings, so bend them to your process. `summary` counts
`paid` as earned and everything else in-flight as pipeline. The DB (`gigs.db`)
is gitignored; `export` gives you a shareable `gigs.md` snapshot.
