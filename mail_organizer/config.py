from __future__ import annotations

from dataclasses import dataclass
from mail_organizer.models import Category


@dataclass
class CategoryAction:
    label_name: str | None
    archive: bool
    trash: bool
    color: str
    icon: str


CATEGORY_CONFIG: dict[Category, CategoryAction] = {
    Category.ACTION: CategoryAction(
        label_name="@Action",
        archive=False,
        trash=False,
        color="#E74C3C",
        icon="🔴",
    ),
    Category.IMPORTANT: CategoryAction(
        label_name="@Important",
        archive=False,
        trash=False,
        color="#F39C12",
        icon="⭐",
    ),
    Category.FYI: CategoryAction(
        label_name="@FYI",
        archive=True,
        trash=False,
        color="#3498DB",
        icon="ℹ️",
    ),
    Category.NEWSLETTER: CategoryAction(
        label_name="@Newsletter",
        archive=True,
        trash=False,
        color="#9B59B6",
        icon="📰",
    ),
    Category.SOCIAL: CategoryAction(
        label_name="@Social",
        archive=True,
        trash=False,
        color="#1ABC9C",
        icon="💬",
    ),
    Category.PROMOTIONS: CategoryAction(
        label_name="@Promotions",
        archive=True,
        trash=False,
        color="#E67E22",
        icon="🏷️",
    ),
    Category.SPAM: CategoryAction(
        label_name=None,
        archive=False,
        trash=True,
        color="#95A5A6",
        icon="🗑️",
    ),
    Category.UNCATEGORIZED: CategoryAction(
        label_name=None,
        archive=False,
        trash=False,
        color="#BDC3C7",
        icon="❓",
    ),
}

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://mail.google.com/",
]

DEFAULT_QUERY = "is:inbox"
DEFAULT_MAX_RESULTS = 50

KNOWN_SOCIAL_SENDERS = {
    "facebook", "twitter", "instagram", "linkedin", "pinterest",
    "tiktok", "snapchat", "reddit", "tumblr", "quora",
    "facebookmail.com", "twitter.com", "linkedin.com",
}

KNOWN_PROMO_SENDERS = {
    "noreply", "no-reply", "marketing", "deals", "offers",
    "promotions", "newsletter", "info@", "hello@", "team@",
}
