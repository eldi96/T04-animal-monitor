import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.api.routes import _collect_and_save, get_service


logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")
DAILY_COLLECTION_TIME = time(hour=23, minute=55)


async def run_daily_collection() -> None:
    """Save the completed day's real API aggregate shortly before KST midnight."""
    while True:
        now = datetime.now(KST)
        next_run = datetime.combine(now.date(), DAILY_COLLECTION_TIME, tzinfo=KST)
        if next_run <= now:
            next_run += timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())

        try:
            await _collect_and_save(get_service())
            logger.info("Scheduled KST daily animal-notice collection completed.")
        except HTTPException as error:
            # Route errors are sanitized; never log request URLs or credentials.
            logger.error("Scheduled animal-notice collection failed (HTTP %s).", error.status_code)
        except Exception:
            logger.exception("Scheduled animal-notice collection failed unexpectedly.")
