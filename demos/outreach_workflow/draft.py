"""
Draft generation for the outreach workflow.

Two modes:
  - templated (default, keyless): deterministic mail-merge with a personalized
    opening built from enrichment. Runs with no API key.
  - llm (optional): uses Anthropic to write a tailored draft. Enabled by
    drafting.use_llm: true AND an ANTHROPIC_API_KEY. If enabled without a key
    it raises a clear error and STOPS — it does not silently fall back or fake.

Nothing here sends email. It only produces {subject, body}.
"""
from __future__ import annotations

import os


def _first_name(contact_name: str) -> str:
    import re
    cleaned = re.sub(r"^(dr|mr|mrs|ms|prof)\.?\s+", "", (contact_name or "").strip(), flags=re.I)
    return cleaned.split()[0] if cleaned.split() else "there"


def _personalized_opening(lead: dict) -> str:
    desc = lead.get("site_description", "")
    title = lead.get("site_title", "")
    company = lead.get("company", "your business")
    if desc:
        snippet = desc.rstrip(".")
        return f"Came across {company} — I saw you {_lower_first(snippet)}."
    if title:
        return f"Came across {company} ({title.split('|')[0].split('—')[0].strip()})."
    return f"Came across {company} while looking at {lead.get('category','local')} businesses in the area."


def _lower_first(s: str) -> str:
    return s[0].lower() + s[1:] if s else s


def render_templated(lead: dict, cfg: dict) -> dict:
    d = cfg.get("drafting", {})
    sender = cfg.get("sender", {})
    ctx = {
        "contact_first": _first_name(lead.get("contact_name", "")),
        "company": lead.get("company", "your business"),
        "category": (lead.get("category", "local") or "local").lower(),
        "opening": _personalized_opening(lead),
        "value_prop": d.get("value_prop", "save hours of repetitive work"),
        "use_case": d.get("use_case", "automatic follow-ups and lead capture"),
        "proof_link": d.get("proof_link", "https://github.com/yourname/freelance-ops"),
        "signature": sender.get("signature", sender.get("name", "")),
    }
    subject = d.get("subject", "Quick idea for {company}").format(**ctx)
    body = d.get("template", "Hi {contact_first},\n\n{opening}\n\n{signature}").format(**ctx)
    return {"subject": subject, "body": body, "draft_mode": "templated"}


def render_llm(lead: dict, cfg: dict) -> dict:
    d = cfg.get("drafting", {})
    sender = cfg.get("sender", {})
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "drafting.use_llm is true but ANTHROPIC_API_KEY is not set. "
            "Export it (see .env.example) or set drafting.use_llm: false to use "
            "the keyless templated drafter. Not faking a draft."
        )
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "LLM drafting needs the anthropic package. Run: pip install anthropic\n"
            f"(import error: {e})"
        )

    client = Anthropic(api_key=api_key)
    facts = {
        "company": lead.get("company", ""),
        "contact_name": lead.get("contact_name", ""),
        "category": lead.get("category", ""),
        "site_title": lead.get("site_title", ""),
        "site_description": lead.get("site_description", ""),
    }
    prompt = (
        "Write a short cold outreach email (4-6 sentences, plain text, no subject "
        "line in the body). Sender is a freelance automation/AI-integration "
        "operator. Be specific to the prospect using the facts; no fluff, no "
        "'I hope this finds you well'. End with a single clear call to action for "
        "a 10-minute call.\n\n"
        f"Sender name: {sender.get('name','')}\n"
        f"Prospect facts: {facts}\n"
        f"Relevant proof to reference: {d.get('proof_link','')}\n"
        "Return the email body only."
    )
    msg = client.messages.create(
        model=d.get("model", "claude-haiku-4-5-20251001"),
        max_tokens=d.get("max_tokens", 500),
        messages=[{"role": "user", "content": prompt}],
    )
    body = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text").strip()
    if sender.get("signature") and sender["signature"] not in body:
        body += "\n\n" + sender["signature"]
    subject = d.get("subject", "Quick idea for {company}").format(
        company=lead.get("company", "your business"))
    return {"subject": subject, "body": body, "draft_mode": "llm"}


def make_draft(lead: dict, cfg: dict) -> dict:
    if cfg.get("drafting", {}).get("use_llm", False):
        return render_llm(lead, cfg)
    return render_templated(lead, cfg)
