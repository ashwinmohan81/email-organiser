from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mail_organizer.config import SCOPES

BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BASE_DIR / "tokens"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


def _ensure_tokens_dir() -> None:
    TOKENS_DIR.mkdir(exist_ok=True)


def _token_path(email: str) -> Path:
    safe = email.replace("@", "_at_").replace(".", "_")
    return TOKENS_DIR / f"{safe}.json"


def list_accounts() -> list[str]:
    _ensure_tokens_dir()
    accounts = []
    for f in TOKENS_DIR.glob("*.json"):
        if f.name.startswith("._"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            email = data.get("account_email", f.stem)
            accounts.append(email)
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            continue
    return sorted(accounts)


def add_account() -> str | None:
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_FILE}. Download it from Google Cloud Console "
            "(APIs & Services > Credentials > OAuth 2.0 Client IDs)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)

    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]

    _ensure_tokens_dir()
    token_data = json.loads(creds.to_json())
    token_data["account_email"] = email
    _token_path(email).write_text(json.dumps(token_data, indent=2))

    return email


def get_gmail_service(email: str):
    path = _token_path(email)
    if not path.exists():
        raise FileNotFoundError(f"No token found for {email}")

    data = json.loads(path.read_text())
    creds = Credentials.from_authorized_user_info(data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data = json.loads(creds.to_json())
        token_data["account_email"] = email
        path.write_text(json.dumps(token_data, indent=2))

    return build("gmail", "v1", credentials=creds)


def remove_account(email: str) -> bool:
    path = _token_path(email)
    if path.exists():
        path.unlink()
        return True
    return False
