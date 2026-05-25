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


async def send_telegram(settings: Settings, digest: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    chunks = _telegram_chunks(digest)
    async with httpx.AsyncClient(timeout=25) as client:
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(_TELEGRAM_INTER_MESSAGE_DELAY)
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", 30)
                LOGGER.warning("Telegram flood control: sleeping %ds", retry_after)
                await asyncio.sleep(retry_after)
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": chunk,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
            response.raise_for_status()


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
    path = await save_markdown(settings, digest)
    await send_telegram(settings, digest)
    send_email(settings, digest)
    await send_webhook(settings, digest)
    LOGGER.info("Digest saved to %s", path)
    return path
