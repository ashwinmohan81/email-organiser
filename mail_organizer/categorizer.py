from __future__ import annotations

import json
import re
from mail_organizer.config import KNOWN_PROMO_SENDERS, KNOWN_SOCIAL_SENDERS
from mail_organizer.models import CategorizedEmail, Email

SYSTEM_PROMPT = """You are an expert email organizer. Analyze the emails below and:

1. FIRST, define a set of smart categories that naturally fit these emails. Categories should be specific and useful — for example "Amazon Orders", "Banking & Finance", "Work Requests", "Travel", "Newsletters", "Social Media", "Spam" — NOT generic labels. Create between 4 and 12 categories. Always include a "Spam & Junk" category.

2. THEN, assign every email to exactly one category.

For each category, also specify an "action":
- "keep" = important, stays in inbox
- "archive" = worth keeping but move out of inbox
- "trash" = junk, delete it

Return a JSON object with this exact structure:
{
  "categories": [
    {"name": "Category Name", "action": "keep|archive|trash"}
  ],
  "emails": [
    {"id": "email_id", "category": "Category Name", "reason": "brief reason (max 8 words)"}
  ]
}

Rules:
- Every email must be assigned to a category
- Category names in "emails" must exactly match names in "categories"
- Be specific: "Amazon Orders" is better than "Shopping", "Bank Alerts" is better than "Finance"
- Respond ONLY with valid JSON. No markdown, no explanation."""


def _build_email_prompt(emails: list[Email]) -> str:
    lines = []
    for e in emails:
        lines.append(
            f'ID: {e.id} | From: {e.sender} <{e.sender_email}> | '
            f'Subject: {e.subject} | Snippet: {e.snippet[:150]} | '
            f'Has-Unsubscribe: {e.has_unsubscribe}'
        )
    return "\n".join(lines)


def _parse_smart_response(raw: str, emails: list[Email]) -> tuple[dict[str, str], list[dict]]:
    """Returns (category_actions_map, email_assignments)."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}, []

    if not isinstance(parsed, dict):
        return {}, []

    categories_raw = parsed.get("categories", [])
    emails_raw = parsed.get("emails", parsed.get("results", []))

    cat_actions = {}
    for c in categories_raw:
        if isinstance(c, dict) and "name" in c:
            cat_actions[c["name"]] = c.get("action", "keep")

    assignments = []
    for item in emails_raw:
        if isinstance(item, dict) and "id" in item:
            assignments.append(item)

    return cat_actions, assignments


def categorize_with_gemini(
    emails: list[Email], api_key: str
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = _build_email_prompt(emails)
    response = model.generate_content(
        [{"role": "user", "parts": [SYSTEM_PROMPT + "\n\nEmails:\n" + prompt]}],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    cat_actions, assignments = _parse_smart_response(response.text, emails)
    return _build_results(emails, cat_actions, assignments)


def categorize_with_ollama(
    emails: list[Email], model_name: str = "mistral",
    batch_size: int = 5, progress_callback=None,
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    import ollama

    all_cat_actions: dict[str, str] = {}
    all_assignments: list[dict] = []

    batches = [emails[i:i + batch_size] for i in range(0, len(emails), batch_size)]

    for batch_idx, batch in enumerate(batches):
        if progress_callback:
            progress_callback(batch_idx, len(batches))

        prompt = _build_email_prompt(batch)
        full_prompt = SYSTEM_PROMPT + "\n\nEmails:\n" + prompt

        response = ollama.generate(
            model=model_name,
            prompt=full_prompt,
            format="json",
            options={"temperature": 0.2},
        )

        raw = response.response if hasattr(response, "response") else response.get("response", "")
        cat_actions, assignments = _parse_smart_response(raw, batch)
        all_cat_actions.update(cat_actions)
        all_assignments.extend(assignments)

    if progress_callback:
        progress_callback(len(batches), len(batches))

    return _build_results(emails, all_cat_actions, all_assignments)


def categorize_with_rules(
    emails: list[Email],
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    cat_actions: dict[str, str] = {}
    results = []
    for e in emails:
        cat, reason, action = _apply_rules(e)
        cat_actions[cat] = action
        results.append(CategorizedEmail(email=e, category=cat, reason=reason))
    return results, cat_actions


def _apply_rules(e: Email) -> tuple[str, str, str]:
    addr = e.sender_email.lower()
    subject = e.subject.lower()
    snippet = e.snippet.lower()

    spam_words = ["winner", "lottery", "urgent action", "act now", "click here",
                  "congratulations", "claim your", "free money"]
    if any(w in subject or w in snippet for w in spam_words):
        return "Spam & Junk", "Spam keywords detected", "trash"

    if any(s in addr for s in KNOWN_SOCIAL_SENDERS):
        return "Social Media", "Social media notification", "archive"

    if e.has_unsubscribe:
        if any(kw in addr for kw in ["newsletter", "digest", "weekly", "update"]):
            return "Newsletters", "Newsletter sender pattern", "archive"
        if any(kw in addr for kw in KNOWN_PROMO_SENDERS):
            return "Promotions & Deals", "Promotional sender", "archive"
        return "Newsletters", "Has unsubscribe header", "archive"

    if any(kw in addr for kw in KNOWN_PROMO_SENDERS):
        return "Promotions & Deals", "Promotional sender", "archive"
    if any(w in subject for w in ["sale", "% off", "discount", "deal", "coupon"]):
        return "Promotions & Deals", "Promotional keywords", "archive"

    action_words = ["please", "action required", "respond", "rsvp", "approve",
                    "review", "confirm", "deadline", "asap", "urgent"]
    if any(w in subject or w in snippet for w in action_words):
        return "Action Required", "Action keywords detected", "keep"

    if any(w in subject for w in ["invitation", "meeting", "invite", "calendar"]):
        return "Action Required", "Meeting or calendar invite", "keep"

    if any(w in addr for w in ["amazon", "flipkart", "myntra", "order", "shipping"]):
        return "Orders & Shipping", "Order-related sender", "keep"

    if any(w in subject for w in ["order", "shipped", "delivered", "tracking"]):
        return "Orders & Shipping", "Order-related subject", "keep"

    if any(w in addr for w in ["bank", "hdfc", "icici", "sbi", "axis", "paypal", "razorpay"]):
        return "Banking & Finance", "Financial sender", "keep"

    if any(w in subject for w in ["transaction", "payment", "statement", "balance"]):
        return "Banking & Finance", "Financial keywords", "keep"

    return "General", "No matching rule", "keep"


def _build_results(
    emails: list[Email],
    cat_actions: dict[str, str],
    assignments: list[dict],
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    id_map = {item["id"]: item for item in assignments}

    results = []
    for e in emails:
        info = id_map.get(e.id, {})
        cat = info.get("category", "Uncategorized")
        reason = info.get("reason", "")
        if cat not in cat_actions:
            cat_actions[cat] = "keep"
        results.append(CategorizedEmail(email=e, category=cat, reason=reason))

    return results, cat_actions


def categorize(
    emails: list[Email],
    backend: str = "rules",
    gemini_api_key: str = "",
    ollama_model: str = "mistral",
    progress_callback=None,
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    if not emails:
        return [], {}

    if backend == "gemini" and gemini_api_key:
        try:
            return categorize_with_gemini(emails, gemini_api_key)
        except Exception as exc:
            return (
                [CategorizedEmail(email=e, category="Error", reason=str(exc)) for e in emails],
                {"Error": "keep"},
            )

    if backend == "ollama":
        try:
            return categorize_with_ollama(
                emails, ollama_model,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            return (
                [CategorizedEmail(email=e, category="Error", reason=str(exc)) for e in emails],
                {"Error": "keep"},
            )

    return categorize_with_rules(emails)
