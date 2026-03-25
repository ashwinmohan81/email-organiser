from __future__ import annotations

import base64
import email as email_lib
import re
from email.header import decode_header
from typing import Any

from mail_organizer.models import Email


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _parse_sender(from_header: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)\s*<(.+?)>$", from_header.strip())
    if match:
        name = match.group(1).strip().strip('"').strip("'")
        addr = match.group(2).strip()
        return name or addr, addr
    return from_header.strip(), from_header.strip()


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_emails(
    service: Any,
    max_results: int = 50,
    query: str = "is:inbox",
) -> list[Email]:
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_stub in messages:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_stub["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date", "List-Unsubscribe"],
            )
            .execute()
        )

        headers = msg.get("payload", {}).get("headers", [])
        from_raw = _decode_header_value(_get_header(headers, "From"))
        sender_name, sender_email = _parse_sender(from_raw)
        subject = _decode_header_value(_get_header(headers, "Subject"))
        date = _get_header(headers, "Date")
        has_unsub = bool(_get_header(headers, "List-Unsubscribe"))

        emails.append(
            Email(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                sender=sender_name,
                sender_email=sender_email,
                subject=subject or "(no subject)",
                snippet=msg.get("snippet", ""),
                date=date,
                label_ids=msg.get("labelIds", []),
                has_unsubscribe=has_unsub,
            )
        )

    return emails


def ensure_label(service: Any, label_name: str) -> str:
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]

    body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    return created["id"]


def batch_modify(
    service: Any,
    msg_ids: list[str],
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> None:
    if not msg_ids:
        return

    body: dict[str, Any] = {"ids": msg_ids}
    if add_label_ids:
        body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids

    service.users().messages().batchModify(userId="me", body=body).execute()


def apply_label_and_archive(
    service: Any, msg_ids: list[str], label_name: str
) -> None:
    label_id = ensure_label(service, label_name)
    batch_modify(
        service,
        msg_ids,
        add_label_ids=[label_id],
        remove_label_ids=["INBOX"],
    )


def apply_label_keep_inbox(
    service: Any, msg_ids: list[str], label_name: str
) -> None:
    label_id = ensure_label(service, label_name)
    batch_modify(service, msg_ids, add_label_ids=[label_id])


def archive_emails(service: Any, msg_ids: list[str]) -> None:
    batch_modify(service, msg_ids, remove_label_ids=["INBOX"])


def trash_emails(service: Any, msg_ids: list[str]) -> None:
    for msg_id in msg_ids:
        service.users().messages().trash(userId="me", id=msg_id).execute()
