from __future__ import annotations

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

# Colors and icons auto-assigned to dynamic categories
PALETTE = [
    "#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#9B59B6",
    "#1ABC9C", "#E67E22", "#2980B9", "#C0392B", "#16A085",
    "#8E44AD", "#D35400", "#2ECC71", "#E91E63", "#00BCD4",
]

ICONS = [
    "🔴", "📦", "💼", "🏦", "📰", "💬", "🏷️", "✈️",
    "⭐", "ℹ️", "🛒", "📋", "🔔", "📧", "🗂️",
]

TRASH_KEYWORDS = {"spam", "junk", "trash", "delete", "unwanted"}
ARCHIVE_KEYWORDS = {"newsletter", "social", "promotion", "digest",
                    "notification", "update", "alert", "fyi"}


def get_category_style(name: str, index: int) -> tuple[str, str]:
    """Return (color, icon) for a category by index."""
    color = PALETTE[index % len(PALETTE)]
    icon = ICONS[index % len(ICONS)]
    return color, icon


def infer_action(category_name: str) -> str:
    """Guess the default action for a category based on its name."""
    lower = category_name.lower()
    if any(kw in lower for kw in TRASH_KEYWORDS):
        return "trash"
    if any(kw in lower for kw in ARCHIVE_KEYWORDS):
        return "archive"
    return "keep"


def make_label_name(category_name: str) -> str:
    """Convert a category name to a Gmail label like @CategoryName."""
    clean = category_name.strip().replace(" ", "")
    return f"@{clean}"
