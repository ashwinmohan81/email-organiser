from __future__ import annotations

import json
import os
import re
from typing import Any

from mail_organizer.config import KNOWN_PROMO_SENDERS, KNOWN_SOCIAL_SENDERS
from mail_organizer.models import CategorizedEmail, Category, Email

SYSTEM_PROMPT = """You are an email categorization assistant. Classify each email into exactly one category.

Categories:
- Action Required: emails that need a response or action (meeting invites, questions, requests, approvals)
- Important: significant emails that should be read but don't require immediate action (updates from boss, financial statements, shipping confirmations for orders)
- FYI: informational emails worth keeping (team updates, announcements, automated reports)
- Newsletter: subscription emails, digests, blog updates, weekly roundups
- Social: notifications from social media platforms (Facebook, LinkedIn, Twitter, Instagram, etc.)
- Promotions: marketing emails, sales, coupons, product launches, deals
- Spam: unwanted junk, phishing attempts, scams, unsolicited bulk email

Return a JSON object with key "results" containing an array. Each element must have:
- "id": the email ID (string)
- "category": one of "Action Required", "Important", "FYI", "Newsletter", "Social", "Promotions", "Spam"
- "reason": a brief reason for the classification (max 10 words)

Example: {"results": [{"id": "1", "category": "Action Required", "reason": "Needs approval"}]}

Respond ONLY with valid JSON. No markdown, no explanation."""


def _build_email_prompt(emails: list[Email]) -> str:
    lines = []
    for e in emails:
        lines.append(
            f'ID: {e.id} | From: {e.sender} <{e.sender_email}> | '
            f'Subject: {e.subject} | Snippet: {e.snippet[:150]} | '
            f'Has-Unsubscribe: {e.has_unsubscribe}'
        )
    return "\n".join(lines)


def _parse_ai_response(raw: str, emails: list[Email]) -> dict[str, tuple[Category, str]]:
    cleaned = raw.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}

    # Handle both bare arrays and wrapped objects like {"emails": [...]}
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                items = v
                break
        else:
            items = [parsed]
    else:
        return {}

    cat_map = {c.value: c for c in Category}
    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        eid = item.get("id", "")
        cat_str = item.get("category", "")
        reason = item.get("reason", "")
        cat = cat_map.get(cat_str, Category.UNCATEGORIZED)
        result[eid] = (cat, reason)

    return result


def categorize_with_gemini(
    emails: list[Email], api_key: str
) -> list[CategorizedEmail]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = _build_email_prompt(emails)
    response = model.generate_content(
        [
            {"role": "user", "parts": [SYSTEM_PROMPT + "\n\nEmails:\n" + prompt]},
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    mapping = _parse_ai_response(response.text, emails)
    return [
        CategorizedEmail(
            email=e,
            category=mapping.get(e.id, (Category.UNCATEGORIZED, ""))[0],
            reason=mapping.get(e.id, (Category.UNCATEGORIZED, "No classification"))[1],
        )
        for e in emails
    ]


def categorize_with_ollama(
    emails: list[Email], model_name: str = "mistral"
) -> list[CategorizedEmail]:
    import ollama

    prompt = _build_email_prompt(emails)
    full_prompt = SYSTEM_PROMPT + "\n\nEmails:\n" + prompt

    response = ollama.generate(
        model=model_name,
        prompt=full_prompt,
        format="json",
        options={"temperature": 0.1},
    )

    raw = response.response if hasattr(response, "response") else response.get("response", "")

    mapping = _parse_ai_response(raw, emails)
    return [
        CategorizedEmail(
            email=e,
            category=mapping.get(e.id, (Category.UNCATEGORIZED, ""))[0],
            reason=mapping.get(e.id, (Category.UNCATEGORIZED, "No classification"))[1],
        )
        for e in emails
    ]


def categorize_with_rules(emails: list[Email]) -> list[CategorizedEmail]:
    results = []
    for e in emails:
        cat, reason = _apply_rules(e)
        results.append(CategorizedEmail(email=e, category=cat, reason=reason))
    return results


def _apply_rules(e: Email) -> tuple[Category, str]:
    addr = e.sender_email.lower()
    subject = e.subject.lower()
    snippet = e.snippet.lower()

    # Spam signals
    spam_words = ["winner", "lottery", "urgent action", "act now", "click here",
                  "congratulations", "claim your", "free money"]
    if any(w in subject or w in snippet for w in spam_words):
        return Category.SPAM, "Spam keywords detected"

    # Newsletter
    if e.has_unsubscribe:
        domain = addr.split("@")[-1] if "@" in addr else ""
        if any(s in addr for s in KNOWN_SOCIAL_SENDERS) or any(
            s in domain for s in KNOWN_SOCIAL_SENDERS
        ):
            return Category.SOCIAL, "Social media notification"

        if any(kw in addr for kw in ["newsletter", "digest", "weekly", "update"]):
            return Category.NEWSLETTER, "Newsletter sender pattern"

        if any(kw in addr for kw in KNOWN_PROMO_SENDERS):
            return Category.PROMOTIONS, "Promotional sender pattern"

        return Category.NEWSLETTER, "Has unsubscribe header"

    # Social
    if any(s in addr for s in KNOWN_SOCIAL_SENDERS):
        return Category.SOCIAL, "Known social media sender"

    # Promotions
    if any(s in addr for s in KNOWN_PROMO_SENDERS):
        return Category.PROMOTIONS, "Promotional sender pattern"
    if any(w in subject for w in ["sale", "% off", "discount", "deal", "coupon", "offer"]):
        return Category.PROMOTIONS, "Promotional subject keywords"

    # Action required signals
    action_words = ["please", "action required", "respond", "rsvp", "approve",
                    "review", "confirm", "deadline", "asap", "urgent"]
    if any(w in subject or w in snippet for w in action_words):
        return Category.ACTION, "Action keywords detected"

    # Calendar/meeting
    if any(w in subject for w in ["invitation", "meeting", "invite", "calendar"]):
        return Category.ACTION, "Meeting or calendar invite"

    return Category.UNCATEGORIZED, "No matching rule"


def categorize(
    emails: list[Email],
    backend: str = "rules",
    gemini_api_key: str = "",
    ollama_model: str = "mistral",
) -> list[CategorizedEmail]:
    if not emails:
        return []

    if backend == "gemini" and gemini_api_key:
        try:
            return categorize_with_gemini(emails, gemini_api_key)
        except Exception as exc:
            return [
                CategorizedEmail(email=e, category=Category.UNCATEGORIZED,
                                 reason=f"Gemini error: {exc}")
                for e in emails
            ]

    if backend == "ollama":
        try:
            return categorize_with_ollama(emails, ollama_model)
        except Exception as exc:
            return [
                CategorizedEmail(email=e, category=Category.UNCATEGORIZED,
                                 reason=f"Ollama error: {exc}")
                for e in emails
            ]

    return categorize_with_rules(emails)
