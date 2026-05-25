import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import httpx

from .config import Settings

LOGGER = logging.getLogger(__name__)


async def save_markdown(settings: Settings, digest: str) -> Path:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    path = settings.output_dir / f"sci-digest-{datetime.now().date().isoformat()}.md"
    path.write_text(digest, encoding="utf-8")
    return path


async def send_telegram(settings: Settings, digest: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    chunks = [digest[index : index + 3900] for index in range(0, len(digest), 3900)]
    async with httpx.AsyncClient(timeout=25) as client:
        for chunk in chunks:
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()


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

