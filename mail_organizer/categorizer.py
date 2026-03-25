from __future__ import annotations

import json
import re
from mail_organizer.config import KNOWN_PROMO_SENDERS, KNOWN_SOCIAL_SENDERS
from mail_organizer.models import CategorizedEmail, Email

# Pass 1: define categories from a compact overview of all emails
CATEGORIES_PROMPT = """You are an expert email organizer. Below is a summary of emails in someone's inbox.

Analyze the senders and subjects and define a set of **smart categories** to organize them.

Rules:
- Create between 4 and 10 categories. Fewer is better — group related emails together.
- Categories should be specific and useful: "Amazon Orders" not "Shopping", "Bank Alerts" not "Finance"
- Group all emails from the same service/company together (e.g. all Amazon emails = one category, all bank emails = one category)
- If a type of email has only 1-2 instances, merge it into a broader category (e.g. one Uber receipt + one flight booking = "Receipts & Travel", NOT two separate categories)
- Always include a "Spam & Junk" category for unwanted emails
- For each category, specify an action:
  - "keep" = important, stays in inbox (personal messages, action items, orders)
  - "archive" = worth keeping but out of inbox (newsletters, notifications, social)
  - "trash" = junk, delete it (spam, scams)

Return ONLY valid JSON:
{"categories": [{"name": "Category Name", "action": "keep|archive|trash"}]}"""


# Pass 2: assign emails to the pre-defined categories
ASSIGN_PROMPT_TEMPLATE = """Assign each email below to exactly one of these categories: {cat_list}

Rules:
- Category name must EXACTLY match one from the list above
- Every email must be assigned — do not skip any
- Lottery/prize/scam emails go to "Spam & Junk"
- When unsure, pick the closest matching category

Return ONLY valid JSON:
{{"results": [{{"id": "email_id", "category": "Category Name", "reason": "brief reason (max 8 words)"}}]}}"""


def _build_compact_summary(emails: list[Email]) -> str:
    lines = []
    for e in emails:
        unsub = " [unsubscribe]" if e.has_unsubscribe else ""
        lines.append(f"From: {e.sender_email} | Subject: {e.subject}{unsub}")
    return "\n".join(lines)


def _build_email_prompt(emails: list[Email]) -> str:
    lines = []
    for e in emails:
        lines.append(
            f'ID: {e.id} | From: {e.sender} <{e.sender_email}> | '
            f'Subject: {e.subject} | Snippet: {e.snippet[:120]} | '
            f'Has-Unsubscribe: {e.has_unsubscribe}'
        )
    return "\n".join(lines)


def _parse_categories_response(raw: str) -> dict[str, str]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    categories_raw = parsed.get("categories", [])
    if isinstance(parsed, dict) and not categories_raw:
        for v in parsed.values():
            if isinstance(v, list):
                categories_raw = v
                break

    cat_actions = {}
    for c in categories_raw:
        if isinstance(c, dict) and "name" in c:
            cat_actions[c["name"]] = c.get("action", "keep")
    return cat_actions


def _parse_assignments(raw: str) -> list[dict]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

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
        return []

    return [item for item in items if isinstance(item, dict) and "id" in item]


def categorize_with_gemini(
    emails: list[Email], api_key: str
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Pass 1: define categories
    summary = _build_compact_summary(emails)
    resp1 = model.generate_content(
        [{"role": "user", "parts": [CATEGORIES_PROMPT + "\n\nEmails:\n" + summary]}],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json", temperature=0.2,
        ),
    )
    cat_actions = _parse_categories_response(resp1.text)
    if not cat_actions:
        cat_actions = {"General": "keep", "Spam & Junk": "trash"}

    # Pass 2: assign all at once (Gemini handles large prompts well)
    cat_list = ", ".join(f'"{c}"' for c in cat_actions)
    assign_prompt = ASSIGN_PROMPT_TEMPLATE.format(cat_list=cat_list)
    email_data = _build_email_prompt(emails)
    resp2 = model.generate_content(
        [{"role": "user", "parts": [assign_prompt + "\n\nEmails:\n" + email_data]}],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json", temperature=0.1,
        ),
    )
    assignments = _parse_assignments(resp2.text)
    return _build_results(emails, cat_actions, assignments)


def categorize_with_ollama(
    emails: list[Email], model_name: str = "mistral",
    batch_size: int = 8, progress_callback=None,
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    import ollama

    total_steps = 1 + len(range(0, len(emails), batch_size))  # 1 for category pass

    # ── Pass 1: define categories (single call, compact summary) ──
    if progress_callback:
        progress_callback(0, total_steps, "Analyzing inbox patterns...")

    summary = _build_compact_summary(emails)
    resp1 = ollama.generate(
        model=model_name,
        prompt=CATEGORIES_PROMPT + "\n\nEmails:\n" + summary,
        format="json",
        options={"temperature": 0.2},
    )
    raw1 = resp1.response if hasattr(resp1, "response") else resp1.get("response", "")
    cat_actions = _parse_categories_response(raw1)
    if not cat_actions:
        cat_actions = {"General": "keep", "Spam & Junk": "trash"}

    # ── Pass 2: assign in batches using fixed category list ──
    cat_list = ", ".join(f'"{c}"' for c in cat_actions)
    assign_prompt = ASSIGN_PROMPT_TEMPLATE.format(cat_list=cat_list)

    all_assignments: list[dict] = []
    batches = [emails[i:i + batch_size] for i in range(0, len(emails), batch_size)]

    for batch_idx, batch in enumerate(batches):
        if progress_callback:
            progress_callback(1 + batch_idx, total_steps, f"Classifying batch {batch_idx + 1}/{len(batches)}...")

        email_data = _build_email_prompt(batch)
        resp = ollama.generate(
            model=model_name,
            prompt=assign_prompt + "\n\nEmails:\n" + email_data,
            format="json",
            options={"temperature": 0.1},
        )
        raw = resp.response if hasattr(resp, "response") else resp.get("response", "")
        assignments = _parse_assignments(raw)
        all_assignments.extend(assignments)

    if progress_callback:
        progress_callback(total_steps, total_steps, "Done!")

    return _build_results(emails, cat_actions, all_assignments)


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

    if any(w in addr for w in ["amazon", "flipkart", "myntra"]):
        return "Orders & Deliveries", "Shopping sender", "keep"
    if any(w in subject for w in ["order", "shipped", "delivered", "tracking", "dispatch"]):
        return "Orders & Deliveries", "Order-related subject", "keep"

    if any(w in addr for w in ["bank", "hdfc", "icici", "sbi", "axis", "paypal",
                                "razorpay", "gpay", "phonepe"]):
        return "Banking & Finance", "Financial sender", "keep"
    if any(w in subject for w in ["transaction", "payment", "statement", "balance", "credited", "debited"]):
        return "Banking & Finance", "Financial keywords", "keep"

    if e.has_unsubscribe:
        if any(kw in addr for kw in KNOWN_PROMO_SENDERS) or any(
            w in subject for w in ["sale", "% off", "discount", "deal", "coupon"]
        ):
            return "Promotions & Deals", "Promotional email", "archive"
        return "Newsletters & Updates", "Has unsubscribe header", "archive"

    if any(kw in addr for kw in KNOWN_PROMO_SENDERS):
        return "Promotions & Deals", "Promotional sender", "archive"

    action_words = ["please", "action required", "respond", "rsvp", "approve",
                    "review", "confirm", "deadline", "asap", "urgent"]
    if any(w in subject or w in snippet for w in action_words):
        return "Action Required", "Needs response", "keep"

    if any(w in subject for w in ["invitation", "meeting", "invite", "calendar"]):
        return "Action Required", "Meeting invite", "keep"

    return "General", "No specific pattern", "keep"


def _merge_small_categories(
    results: list[CategorizedEmail],
    cat_actions: dict[str, str],
    min_size: int = 2,
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    """Merge categories with fewer than min_size emails into 'General'."""
    from collections import Counter
    counts = Counter(r.category for r in results)

    small = {cat for cat, n in counts.items() if n < min_size and cat != "Spam & Junk"}
    if not small:
        return results, cat_actions

    fallback = "General"
    if fallback not in cat_actions:
        cat_actions[fallback] = "keep"

    merged = []
    for r in results:
        if r.category in small:
            merged.append(CategorizedEmail(email=r.email, category=fallback, reason=r.reason))
        else:
            merged.append(r)

    for cat in small:
        cat_actions.pop(cat, None)

    return merged, cat_actions


def _build_results(
    emails: list[Email],
    cat_actions: dict[str, str],
    assignments: list[dict],
) -> tuple[list[CategorizedEmail], dict[str, str]]:
    id_map = {item["id"]: item for item in assignments}

    results = []
    for e in emails:
        info = id_map.get(e.id, {})
        cat = info.get("category", "General")
        reason = info.get("reason", "")
        if cat not in cat_actions:
            cat_actions[cat] = "keep"
        results.append(CategorizedEmail(email=e, category=cat, reason=reason))

    return _merge_small_categories(results, cat_actions)


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
