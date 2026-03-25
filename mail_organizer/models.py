from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Email:
    id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    snippet: str
    date: str
    label_ids: list[str] = field(default_factory=list)
    has_unsubscribe: bool = False

    @property
    def sender_initial(self) -> str:
        name = self.sender or self.sender_email
        return name[0].upper() if name else "?"

    @property
    def sender_display(self) -> str:
        if self.sender and self.sender != self.sender_email:
            return self.sender
        return self.sender_email


@dataclass
class CategoryInfo:
    name: str
    label_name: str
    action: str  # "keep", "archive", "trash"
    color: str = ""
    icon: str = ""


@dataclass
class CategorizedEmail:
    email: Email
    category: str
    reason: str = ""
