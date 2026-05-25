import logging
from datetime import datetime
from html import escape

from .config import Settings
from .delivery import deliver, send_articles_to_telegram
from .enrichment import enrich_findings
from .queries import all_news_queries, load_queries
from .relevance import filter_relevant
from .render import render_digest
from .scoring import dedupe_and_rank
from .sources import collect_findings
from .state import SentHistory
from .summarizer import build_ai_brief

LOGGER = logging.getLogger(__name__)


def _build_header(count: int, ai_brief: str | None) -> str:
    date = datetime.now().date()
    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    date_str = f"{date.day} {months[date.month]} {date.year}"
    header = (
        f"<b>🧬 SCI Treatment Radar — {date_str}</b>\n"
        f"Новых материалов по теме лечения ТСМ: <b>{count}</b>\n"
        "Источники: PubMed · ClinicalTrials.gov · Google News"
    )
    if ai_brief:
        header += f"\n\n{escape(ai_brief)}"
    return header


async def run_digest(settings: Settings) -> str:
    query_config = load_queries(settings.queries_path)
    queries = all_news_queries(query_config)
    raw_findings = await collect_findings(queries, settings.digest_lookback_days)
    relevant_findings = filter_relevant(raw_findings)
    ranked_findings = dedupe_and_rank(
        relevant_findings,
        query_config.get("high_priority_keywords", []),
        settings.digest_max_items * 4,
    )
    history = SentHistory(settings.state_path)
    findings = history.filter_new(ranked_findings)[: settings.digest_max_items]

    ai_brief = await build_ai_brief(settings, findings)

    # Enrich: OG image + short URL + Russian title (concurrent)
    enriched = await enrich_findings(findings)

    # Telegram: photo-per-article visual format
    header = _build_header(len(enriched), ai_brief)
    await send_articles_to_telegram(settings, enriched, header=header)

    # Markdown archive + email/webhook (plain text digest)
    digest = render_digest(findings, ai_brief)
    path = await deliver(settings, digest)

    history.mark_sent(findings)
    LOGGER.info("Built digest with %d findings: %s", len(findings), path)
    return digest
