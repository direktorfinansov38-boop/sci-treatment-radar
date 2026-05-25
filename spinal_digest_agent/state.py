import json
from datetime import UTC, datetime
from pathlib import Path

from .models import Finding


class SentHistory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"items": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _keys_for(self, finding: Finding) -> set[str]:
        keys = {f"title:{finding.dedupe_key}"}
        if finding.url:
            keys.add(f"url:{finding.url.strip().lower()}")
        return keys

    def has_seen(self, finding: Finding) -> bool:
        items = self._data.get("items", {})
        return any(key in items for key in self._keys_for(finding))

    def filter_new(self, findings: list[Finding]) -> list[Finding]:
        return [finding for finding in findings if not self.has_seen(finding)]

    def mark_sent(self, findings: list[Finding]) -> None:
        now = datetime.now(UTC).isoformat()
        items = self._data.setdefault("items", {})
        for finding in findings:
            payload = {
                "title": finding.title,
                "url": finding.url,
                "source": finding.source,
                "sent_at": now,
                "published_at": finding.published_at.isoformat() if finding.published_at else None,
            }
            for key in self._keys_for(finding):
                items[key] = payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)
