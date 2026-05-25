from datetime import UTC, datetime, timedelta

from .models import Finding

_RECENCY_TIERS = [
    (timedelta(days=1), 10),
    (timedelta(days=2), 6),
    (timedelta(days=3), 3),
]


def score_finding(finding: Finding, high_priority_keywords: list[str]) -> Finding:
    text = f"{finding.title} {finding.summary}".lower()
    score = 10
    tags: list[str] = []

    if finding.region:
        score += 8
        tags.append(finding.region)

    for keyword in high_priority_keywords:
        if keyword.lower() in text:
            score += 5
            tags.append(keyword)

    if "clinical trial" in text or "клиничес" in text:
        score += 8
    if "device" in text or "implant" in text or "аппарат" in text:
        score += 6
    if "phase" in text or "first-in-human" in text:
        score += 6

    # Recency bonus: fresher articles rank higher when scores are equal
    if finding.published_at:
        age = datetime.now(UTC) - finding.published_at
        for threshold, bonus in _RECENCY_TIERS:
            if age <= threshold:
                score += bonus
                break

    unique_tags = tuple(dict.fromkeys(tags))
    return Finding(
        title=finding.title,
        url=finding.url,
        source=finding.source,
        published_at=finding.published_at,
        summary=finding.summary,
        region=finding.region,
        score=score,
        tags=unique_tags,
    )


def dedupe_and_rank(findings: list[Finding], high_priority_keywords: list[str], limit: int) -> list[Finding]:
    deduped: dict[str, Finding] = {}
    for finding in findings:
        scored = score_finding(finding, high_priority_keywords)
        existing = deduped.get(scored.dedupe_key)
        if existing is None or scored.score > existing.score:
            deduped[scored.dedupe_key] = scored

    return sorted(
        deduped.values(),
        key=lambda item: (item.score, item.published_at is not None, item.published_at),
        reverse=True,
    )[:limit]

