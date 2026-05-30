import asyncio
import html
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Finding

LOGGER = logging.getLogger(__name__)


def _cutoff(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    return BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, str | int]) -> dict:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def fetch_google_news_rss(
    client: httpx.AsyncClient,
    query: str,
    region: str | None,
    lookback_days: int,
) -> list[Finding]:
    cutoff = _cutoff(lookback_days)
    url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query + ' when:' + str(lookback_days) + 'd')}&hl=en-US&gl=US&ceid=US:en"
    )
    raw_text = (await client.get(url, timeout=20)).text
    # feedparser is synchronous — run in executor to avoid blocking the event loop
    feed = await asyncio.get_event_loop().run_in_executor(None, feedparser.parse, raw_text)
    findings: list[Finding] = []
    for entry in feed.entries:
        published = _parse_date(getattr(entry, "published", None))
        if published and published < cutoff:
            continue
        findings.append(
            Finding(
                title=_clean_html(getattr(entry, "title", "")),
                url=getattr(entry, "link", ""),
                source="Google News",
                published_at=published,
                summary=_clean_html(getattr(entry, "summary", "")),
                region=region,
            )
        )
    return findings


async def fetch_pubmed(client: httpx.AsyncClient, lookback_days: int) -> list[Finding]:
    cutoff = _cutoff(lookback_days)
    search = await _get_json(
        client,
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        {
            "db": "pubmed",
            "term": (
                '("spinal cord injury"[Title/Abstract]) AND '
                "("
                "treatment OR therapy OR neurostimulation OR regeneration OR implant OR "
                "\"stem cell\" OR \"stem cells\" OR \"cell therapy\" OR "
                "\"mesenchymal stem cell\" OR \"mesenchymal stem cells\" OR MSC OR "
                "\"neural stem cell\" OR \"neural stem cells\" OR NSC OR "
                "\"induced pluripotent stem cell\" OR iPSC OR "
                "\"cell transplantation\" OR exosome OR \"extracellular vesicle\" OR "
                "\"Schwann cell\" OR \"olfactory ensheathing cell\""
                ")"
            ),
            "retmode": "json",
            "retmax": 30,
            "sort": "pub date",
            "reldate": lookback_days,
            "datetype": "pdat",
        },
    )
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary = await _get_json(
        client,
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        {"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
    )
    result = summary.get("result", {})
    findings: list[Finding] = []
    for pmid in ids:
        item = result.get(pmid, {})
        published = _parse_date(item.get("pubdate"))
        if published and published < cutoff:
            continue
        findings.append(
            Finding(
                title=item.get("title", "").rstrip("."),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source="PubMed",
                published_at=published,
                summary=item.get("source", ""),
            )
        )
    return findings


async def fetch_clinical_trials(client: httpx.AsyncClient, lookback_days: int) -> list[Finding]:
    cutoff = _cutoff(lookback_days)
    response = await _get_json(
        client,
        "https://clinicaltrials.gov/api/v2/studies",
        {
            "query.term": (
                "spinal cord injury treatment OR spinal cord injury neurostimulation OR "
                "spinal cord injury stem cell OR spinal cord injury cell therapy OR "
                "spinal cord injury mesenchymal stem cells OR spinal cord injury neural stem cells OR "
                "spinal cord injury cell transplantation OR spinal cord injury exosomes"
            ),
            "pageSize": 50,
            "sort": "@lastUpdatePostDate:desc",
        },
    )
    findings: list[Finding] = []
    for study in response.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        conditions = protocol.get("conditionsModule", {}).get("conditions", [])
        last_update = _parse_date(status.get("lastUpdatePostDateStruct", {}).get("date"))
        if last_update and last_update < cutoff:
            continue
        nct_id = identification.get("nctId")
        title = identification.get("briefTitle") or identification.get("officialTitle") or nct_id
        phase = ", ".join(design.get("phases", []))
        summary = "; ".join(part for part in [phase, ", ".join(conditions[:3])] if part)
        findings.append(
            Finding(
                title=title,
                url=f"https://clinicaltrials.gov/study/{nct_id}",
                source="ClinicalTrials.gov",
                published_at=last_update,
                summary=summary,
            )
        )
    return findings


_RU_SCI_KEYWORDS = frozenset([
    "спинной мозг", "стволовые клетки", "клеточная терапия",
    "нейростимуляция", "экзоскелет", "параплегия", "тетраплегия",
    "нейроинтерфейс", "нейромат", "матриселф",
    "клеточная трансплантация", "мезенхимальные",
    "нейральные стволовые", "экзосомы", "регенерация нерв",
])

_RUSSIAN_RSS_FEEDS = [
    ("https://ria.ru/export/rss2/science/index.xml", "РИА Новости"),
    ("https://tass.ru/rss/v2.xml", "ТАСС"),
    ("https://naked-science.ru/feed/", "Naked Science"),
    ("https://medvestnik.ru/rss", "Медвестник"),
]


async def fetch_russian_rss_sources(
    client: httpx.AsyncClient,
    lookback_days: int,
) -> list[Finding]:
    cutoff = _cutoff(lookback_days)
    findings: list[Finding] = []
    for feed_url, source_name in _RUSSIAN_RSS_FEEDS:
        try:
            response = await client.get(
                feed_url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SCI-Radar/1.0)"},
            )
            feed = await asyncio.get_event_loop().run_in_executor(None, feedparser.parse, response.text)
            for entry in feed.entries:
                title = _clean_html(getattr(entry, "title", ""))
                url_entry = getattr(entry, "link", "")
                summary = _clean_html(getattr(entry, "summary", ""))
                if not title or not url_entry:
                    continue
                text = (title + " " + summary).lower()
                if not any(kw in text for kw in _RU_SCI_KEYWORDS):
                    continue
                published = _parse_date(getattr(entry, "published", None))
                if published and published < cutoff:
                    continue
                findings.append(
                    Finding(
                        title=title,
                        url=url_entry,
                        source=source_name,
                        published_at=published,
                        summary=summary,
                        region="Russia",
                    )
                )
        except Exception as exc:
            LOGGER.warning("Russian RSS failed for %s: %s", source_name, exc)
    return findings


async def collect_findings(
    queries: list[tuple[str, str | None]],
    yandex_queries: list[str],
    lookback_days: int,
) -> list[Finding]:
    timeout = httpx.Timeout(25)
    headers = {"User-Agent": "SCI-Treatment-Radar/0.1 (+https://github.com/)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        # Российские источники идут первыми — прямые RSS-ленты (без гео-блокировки)
        coros: list = [fetch_russian_rss_sources(client, lookback_days)]
        coros.extend(
            fetch_google_news_rss(client, query, region, lookback_days)
            for query, region in queries
        )
        coros.extend([fetch_pubmed(client, lookback_days), fetch_clinical_trials(client, lookback_days)])

        # Run all sources concurrently; return_exceptions so one failure doesn't cancel others
        results = await asyncio.gather(*coros, return_exceptions=True)
        findings: list[Finding] = []
        for result in results:
            if isinstance(result, Exception):
                LOGGER.warning("Source failed: %s", result)
            else:
                findings.extend(result)
        return findings
