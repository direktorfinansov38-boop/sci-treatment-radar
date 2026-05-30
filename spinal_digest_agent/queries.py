import json
from pathlib import Path
from typing import Any


def load_queries(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def all_yandex_queries(query_config: dict[str, Any]) -> list[str]:
    return query_config.get("yandex_terms", [])


def all_news_queries(query_config: dict[str, Any]) -> list[tuple[str, str | None]]:
    rows: list[tuple[str, str | None]] = []
    for term in query_config.get("core_terms", []):
        rows.append((term, None))
    for region, terms in query_config.get("priority_regions", {}).items():
        for term in terms:
            rows.append((term, region))
    return rows

