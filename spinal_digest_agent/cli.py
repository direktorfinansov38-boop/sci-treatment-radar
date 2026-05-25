import argparse
import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import Settings
from .pipeline import run_digest


def main() -> None:
    parser = argparse.ArgumentParser(prog="spinal_digest_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once", help="Build and send one digest now")
    subparsers.add_parser("serve", help="Run daily scheduler")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = Settings()

    if args.command == "run-once":
        asyncio.run(run_digest(settings))
        return

    scheduler = BlockingScheduler(timezone=settings.digest_timezone)
    scheduler.add_job(
        lambda: asyncio.run(run_digest(settings)),
        trigger="cron",
        hour=settings.digest_hour,
        minute=settings.digest_minute,
        id="daily_spinal_digest",
        replace_existing=True,
    )
    logging.info(
        "Scheduler started: daily at %02d:%02d %s",
        settings.digest_hour,
        settings.digest_minute,
        settings.digest_timezone,
    )
    scheduler.start()
