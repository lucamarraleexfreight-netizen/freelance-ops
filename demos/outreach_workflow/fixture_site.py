#!/usr/bin/env python3
"""
Local homepage fixture for the outreach demo.

Lets the enrichment step run OFFLINE: serves a plausible business homepage for
any /slug path, with a <title>, meta description, and social links to detect.
In production, enrichment fetches the client's real website instead.

Run:  python3 fixture_site.py            # http://127.0.0.1:8801/<slug>
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BLURBS = {
    "acmeplumbing": ("Acme Plumbing — Emergency & Residential Plumbers in Austin",
                     "24/7 emergency plumbing, water heater installs, and drain cleaning for Austin homeowners since 2004."),
    "brightsmiledental": ("BrightSmile Dental | Family & Cosmetic Dentistry",
                          "A modern family dental practice offering cleanings, whitening, and Invisalign in downtown Denver."),
    "peakroofing": ("Peak Roofing Co. — Roof Repair & Replacement",
                    "Storm-damage roofing specialists. Free inspections and insurance-claim help across the Nashville metro."),
    "greenleaflandscaping": ("GreenLeaf Landscaping — Design, Install, Maintain",
                             "Full-service landscaping: design, irrigation, and weekly maintenance for Portland yards."),
}
DEFAULT = ("{Company} — Local Services",
           "A local business providing professional services to its community.")


def homepage(slug: str) -> str:
    title, desc = BLURBS.get(slug, (DEFAULT[0].replace("{Company}", slug.title()), DEFAULT[1]))
    return f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta property="og:description" content="{desc}">
</head><body>
  <h1>{title}</h1>
  <p>{desc}</p>
  <nav>
    <a href="https://www.facebook.com/{slug}">Facebook</a>
    <a href="https://www.linkedin.com/company/{slug}">LinkedIn</a>
    <a href="https://www.instagram.com/{slug}">Instagram</a>
    <a href="mailto:info@{slug}.example.com">Email us</a>
  </nav>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        slug = urlparse(self.path).path.strip("/") or "example"
        body = homepage(slug).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Homepage fixture at http://{args.host}:{args.port}/<slug>  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
