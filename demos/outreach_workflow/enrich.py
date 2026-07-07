"""
Keyless enrichment for the outreach workflow.

For each lead it tries to add, using only free/no-key methods:
  - site_title, site_description   (fetch homepage, parse <title> + meta)
  - socials                        (linkedin/facebook/instagram/twitter links)
  - guessed_emails                 (from contact name + domain, pattern-based)
  - email_mx_ok                    (optional DNS MX check; off by default)

Every step degrades gracefully: if a site is unreachable, the fields are left
empty with a note - the pipeline never crashes on a bad URL.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

SOCIAL_DOMAINS = {
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "twitter": "twitter.com",
    "x": "x.com",
}


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _name_parts(contact_name: str):
    cleaned = re.sub(r"^(dr|mr|mrs|ms|prof)\.?\s+", "", contact_name.strip(), flags=re.I)
    bits = [b for b in re.split(r"\s+", cleaned) if b]
    if not bits:
        return "", ""
    first = re.sub(r"[^a-z]", "", bits[0].lower())
    last = re.sub(r"[^a-z]", "", bits[-1].lower()) if len(bits) > 1 else ""
    return first, last


def guess_emails(contact_name: str, domain: str, patterns: list) -> list:
    """Pattern-based email guessing. Pure string logic, no network."""
    first, last = _name_parts(contact_name)
    if not domain or not first:
        return []
    f = first[0] if first else ""
    l = last[0] if last else ""
    out = []
    for pat in patterns:
        local = pat.format(first=first, last=last, f=f, l=l).strip(".")
        if "{" in local or not local:
            continue
        candidate = f"{local}@{domain}"
        if candidate not in out:
            out.append(candidate)
    return out


def mx_ok(domain: str):
    """Return True/False if we could check MX, None if the check is unavailable."""
    if not domain:
        return None
    try:
        import dns.resolver  # dnspython, optional
    except ImportError:
        return None
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(answers) > 0
    except Exception:
        return False


def fetch_homepage(url: str, timeout: int = 10) -> dict:
    result = {"site_title": "", "site_description": "", "socials": {}, "note": ""}
    if not url:
        result["note"] = "no website"
        return result
    if "://" not in url:
        url = "http://" + url
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OutreachEnrich/1.0)"}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except requests.RequestException as e:
        result["note"] = f"fetch failed: {type(e).__name__}"
        return result

    soup = BeautifulSoup(resp.text, "lxml")
    if soup.title and soup.title.string:
        result["site_title"] = " ".join(soup.title.string.split())
    meta = soup.find("meta", attrs={"name": "description"}) or \
        soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        result["site_description"] = " ".join(meta["content"].split())

    socials = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        for name, dom in SOCIAL_DOMAINS.items():
            if dom in href and name not in socials:
                socials[name] = a["href"]
    result["socials"] = socials
    return result


def enrich_lead(lead: dict, cfg: dict) -> dict:
    """Return a copy of lead with enrichment fields added."""
    out = dict(lead)
    enr_cfg = cfg.get("enrichment", {})
    guess_cfg = cfg.get("email_guess", {})

    if enr_cfg.get("fetch_homepage", True):
        page = fetch_homepage(lead.get("website", ""), enr_cfg.get("timeout", 10))
        out.update({
            "site_title": page["site_title"],
            "site_description": page["site_description"],
            "socials": page["socials"],
            "enrich_note": page["note"],
        })
    else:
        out.update({"site_title": "", "site_description": "", "socials": {}, "enrich_note": "skipped"})

    # Email domain: explicit 'domain' column wins, else derive from the website.
    email_domain = (lead.get("domain") or "").strip() or domain_from_url(lead.get("website", ""))

    # Email: keep given one, else guess.
    if not lead.get("email"):
        guesses = guess_emails(
            lead.get("contact_name", ""),
            email_domain,
            guess_cfg.get("patterns", ["{first}", "{first}.{last}", "{f}{last}"]),
        )
        out["guessed_emails"] = guesses
        out["email"] = guesses[0] if guesses else ""
        out["email_source"] = "guessed" if guesses else "none"
    else:
        out["guessed_emails"] = []
        out["email_source"] = "provided"

    if guess_cfg.get("verify_mx", False) and out.get("email"):
        out["email_mx_ok"] = mx_ok(email_domain)
    else:
        out["email_mx_ok"] = None
    return out
