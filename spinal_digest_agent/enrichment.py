"""Enrich findings with OG image, short URL, and Russian title."""
import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from .models import Finding

LOGGER = logging.getLogger(__name__)

_RU_CHARS = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def _is_russian(text: str) -> bool:
    if not text:
        return True
    ru = sum(1 for c in text if c in _RU_CHARS)
    return ru / len(text) > 0.35


async def _fetch_og_image(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url, timeout=10, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("meta", property="og:image") or soup.find(
            "meta", attrs={"name": "twitter:image"}
        )
        if tag:
            src = tag.get("content", "")
            if src and src.startswith("http"):
                return src
    except Exception as exc:
        LOGGER.debug("OG image failed %s: %s", url, exc)
    return None


async def _shorten_url(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(
            "https://tinyurl.com/api-create.php",
            params={"url": url},
            timeout=8,
        )
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
    except Exception as exc:
        LOGGER.debug("TinyURL failed %s: %s", url, exc)
    return url


async def _translate_google(client: httpx.AsyncClient, text: str) -> str:
    try:
        resp = await client.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "ru", "dt": "t", "q": text},
            timeout=8,
        )
        data = resp.json()
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or text
    except Exception as exc:
        LOGGER.debug("Translation failed: %s", exc)
    return text


async def _identity(value: str) -> str:
    return value


async def _enrich_one(finding: Finding, client: httpx.AsyncClient) -> Finding:
    translate_coro = (
        _identity(finding.title)
        if _is_russian(finding.title)
        else _translate_google(client, finding.title)
    )
    og_image, short_url, russian_title = await asyncio.gather(
        _fetch_og_image(client, finding.url),
        _shorten_url(client, finding.url),
        translate_coro,
        return_exceptions=True,
    )
    return Finding(
        title=finding.title,
        url=finding.url,
        source=finding.source,
        published_at=finding.published_at,
        summary=finding.summary,
        region=finding.region,
        score=finding.score,
        tags=finding.tags,
        og_image=og_image if isinstance(og_image, str) else None,
        short_url=short_url if isinstance(short_url, str) else finding.url,
        russian_title=russian_title if isinstance(russian_title, str) else finding.title,
    )


async def enrich_findings(findings: list[Finding]) -> list[Finding]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15), headers=headers, follow_redirects=True
    ) as client:
        results = await asyncio.gather(
            *[_enrich_one(f, client) for f in findings],
            return_exceptions=True,
        )

    enriched: list[Finding] = []
    for original, result in zip(findings, results):
        enriched.append(result if isinstance(result, Finding) else original)
    return enriched
