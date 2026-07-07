#!/usr/bin/env python3
"""
Self-contained demo target for the lead scraper.

Serves a paginated "business directory" on localhost so the scraper runs with
ZERO external network access. Data is deterministic (fixed seed) and includes a
few intentional duplicate records so the dedupe logic is observable.

Run:
    python3 serve_fixture.py            # serves on http://127.0.0.1:8799
    python3 serve_fixture.py --port 9000

Pages:
    GET /                       -> redirects to /directory?page=1
    GET /directory?page=N       -> 10 business cards + a "next" link (until last)
    GET /robots.txt             -> permissive
"""
import argparse
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PER_PAGE = 10

CATEGORIES = ["Plumber", "Electrician", "Roofing", "HVAC", "Landscaping",
              "Painting", "Flooring", "Locksmith", "Pest Control", "Cleaning"]
CITIES = [("Austin", "TX"), ("Denver", "CO"), ("Portland", "OR"),
          ("Nashville", "TN"), ("Raleigh", "NC"), ("Tampa", "FL")]
NAMES = ["Summit", "Apex", "Blue Sky", "Pioneer", "Evergreen", "Redline",
         "Cornerstone", "Ironclad", "Beacon", "Trueline", "Northgate",
         "Silverleaf", "Copperfield", "Highpoint", "Riverbend", "Oakmont",
         "Stonewall", "Brightway", "Vanguard", "Keystone", "Falcon", "Granite",
         "Maplewood", "Harborview"]


def _records(seed: int = 7):
    """Deterministic list of business records with 3 injected duplicates."""
    rng = random.Random(seed)
    recs = []
    for i in range(45):
        name_word = NAMES[i % len(NAMES)]
        cat = CATEGORIES[i % len(CATEGORIES)]
        city, st = CITIES[i % len(CITIES)]
        recs.append({
            "name": f"{name_word} {cat} Co.",
            "category": cat,
            "address": f"{rng.randint(100, 9999)} {rng.choice(['Main','Oak','Elm','Pine','Cedar'])} St, {city}, {st}",
            "phone": f"({rng.randint(200,989)}) 555-{rng.randint(1000,9999):04d}",
            "website": f"https://{name_word.lower().replace(' ','')}{cat.lower().replace(' ','')}.example.com",
        })
    # Inject exact duplicates (same name + address) to prove dedupe works.
    recs.insert(5, dict(recs[2]))
    recs.insert(15, dict(recs[10]))
    recs.append(dict(recs[0]))
    return recs


RECORDS = _records()
TOTAL_PAGES = (len(RECORDS) + PER_PAGE - 1) // PER_PAGE


def render_page(page: int) -> str:
    start = (page - 1) * PER_PAGE
    chunk = RECORDS[start:start + PER_PAGE]
    cards = []
    for r in chunk:
        cards.append(f"""
      <div class="card">
        <h2 class="name">{r['name']}</h2>
        <span class="category">{r['category']}</span>
        <span class="address">{r['address']}</span>
        <span class="phone">{r['phone']}</span>
        <a class="website" href="{r['website']}">Website</a>
      </div>""")
    next_link = ""
    if page < TOTAL_PAGES:
        next_link = f'<li class="next"><a href="/directory?page={page + 1}">next &raquo;</a></li>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Demo Business Directory - page {page}</title></head>
<body>
  <h1>Local Business Directory</h1>
  <p>Page {page} of {TOTAL_PAGES}</p>
  <div class="listings">{''.join(cards)}
  </div>
  <ul class="pager">{next_link}</ul>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, status: int = 200, ctype: str = "text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/robots.txt":
            return self._send("User-agent: *\nAllow: /\n", ctype="text/plain")
        if parsed.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/directory?page=1")
            self.end_headers()
            return
        if parsed.path == "/directory":
            qs = parse_qs(parsed.query)
            try:
                page = int(qs.get("page", ["1"])[0])
            except ValueError:
                page = 1
            if page < 1 or page > TOTAL_PAGES:
                # Empty page (no cards) so scrapers can detect the end.
                return self._send("<!doctype html><html><body><div class='listings'></div></body></html>")
            return self._send(render_page(page))
        return self._send("<h1>404</h1>", status=404)

    def log_message(self, *args):  # keep the console quiet
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Demo directory serving at http://{args.host}:{args.port}/directory?page=1 "
          f"({len(RECORDS)} records across {TOTAL_PAGES} pages). Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
