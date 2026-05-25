from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Finding:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str = ""
    region: str | None = None
    score: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def dedupe_key(self) -> str:
        normalized = "".join(ch.lower() for ch in self.title if ch.isalnum())
        return normalized[:140] or self.url.lower()

