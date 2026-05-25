import asyncio
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import httpx

from .config import Settings

LOGGER = logging.getLogger(__name__)

_TELEGRAM_INTER_MESSAGE_DELAY = 1.5  # seconds between chunks to avoid flood control


async def save_markdown(settings: Settings, digest: str) -> Path:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    path = settings.output_dir / f"sci-digest-{datetime.now().date().isoformat()}.md"
    path.write_text(digest, encoding="utf-8")
    return path


async def _tg_post(client: httpx.AsyncClient, bot_token: str, method: str, payload: dict) -> None:
    """Post to Telegram API with flood-control retry."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    response = await client.post(url, json=payload)
    if response.status_code == 429:
        retry_after = response.json().get("parameters", {}).get("retry_after", 30)
        LOGGER.warning("Telegram flood control: sleeping %ds", retry_after)
        await asyncio.sleep(retry_after)
        response = await client.post(url, json=payload)
    response.raise_for_status()


async def send_telegram(settings: Settings, digest: str) -> None:
    """Send full digest as text chunks (used for plain-text fallback / markdown archive)."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    chunks = _telegram_chunks(digest)
    async with httpx.AsyncClient(timeout=25) as client:
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(_TELEGRAM_INTER_MESSAGE_DELAY)
            await _tg_post(
                client,
                settings.telegram_bot_token,
                "sendMessage",
                {
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )


async def send_articles_to_telegram(
    settings: Settings,
    findings: list,
    header: str | None = None,
) -> None:
    """Send each finding as a photo+caption message (new visual format)."""
    from .models import Finding
    from .render import format_article_caption

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    if not findings:
        return

    async with httpx.AsyncClient(timeout=30) as client:
        # Optional header message
        if header:
            await _tg_post(
                client,
                settings.telegram_bot_token,
                "sendMessage",
                {
                    "chat_id": settings.telegram_chat_id,
                    "text": header,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            await asyncio.sleep(_TELEGRAM_INTER_MESSAGE_DELAY)

        for i, finding in enumerate(findings):
            if i > 0:
                await asyncio.sleep(_TELEGRAM_INTER_MESSAGE_DELAY)

            caption = format_article_caption(finding)

            if finding.og_image:
                try:
                    await _tg_post(
                        client,
                        settings.telegram_bot_token,
                        "sendPhoto",
                        {
                            "chat_id": settings.telegram_chat_id,
                            "photo": finding.og_image,
                            "caption": caption,
                            "parse_mode": "HTML",
                        },
                    )
                    continue
                except Exception as exc:
                    LOGGER.debug("sendPhoto failed, falling back to sendMessage: %s", exc)

            # Fallback: text message
            await _tg_post(
                client,
                settings.telegram_bot_token,
                "sendMessage",
                {
                    "chat_id": settings.telegram_chat_id,
                    "text": caption,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
            )


def _telegram_chunks(digest: str, limit: int = 3800) -> list[str]:
    if len(digest) <= limit:
        return [digest]

    chunks: list[str] = []
    current = ""
    for block in digest.split("\n\n━━━━━━━━━━━━\n\n"):
        separator = "\n\n━━━━━━━━━━━━\n\n" if current else ""
        candidate = f"{current}{separator}{block}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = block

    if current:
        chunks.append(current)
    return chunks


def send_email(settings: Settings, digest: str) -> None:
    if not all(
        [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.email_from,
            settings.email_to,
        ]
    ):
        return

    message = EmailMessage()
    message["Subject"] = f"SCI Treatment Radar - {datetime.now().date().isoformat()}"
    message["From"] = settings.email_from
    message["To"] = settings.email_to
    message.set_content(digest)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_webhook(settings: Settings, digest: str) -> None:
    if not settings.webhook_url:
        return
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(settings.webhook_url, json={"text": digest})
        response.raise_for_status()


async def deliver(settings: Settings, digest: str) -> Path:
    """Save markdown + send text digest via email/webhook."""
    path = await save_markdown(settings, digest)
    send_email(settings, digest)
    await send_webhook(settings, digest)
    LOGGER.info("Digest saved to %s", path)
    return path
