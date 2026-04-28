import logging, asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from .config import get_settings
from .database import SessionLocal
from .fetcher import fetch_all
from .models.orm import Station, StationWasteType, SyncMeta

settings = get_settings()
logger = logging.getLogger("sortsmart.scheduler")
scheduler = AsyncIOScheduler()
_next_run: datetime | None = None


_sync_lock = asyncio.Lock()


async def sync_now(db: Session | None = None) -> None:
    global _next_run

    if _sync_lock.locked():
        logger.warning("Sync already in progress, skipping")
        return

    async with _sync_lock:
        owns_session = db is None
        if owns_session:
            db = SessionLocal()

        try:
            ...  # rest of your existing code unchanged
        except Exception as exc:
            logger.error("Sync failed: %s", exc, exc_info=True)
            if owns_session:
                db.rollback()
        finally:
            if owns_session:
                db.close()


def get_next_run() -> datetime | None:
    return _next_run


def start() -> None:
    scheduler.add_job(
        sync_now,
        trigger=IntervalTrigger(hours=settings.refresh_interval_hours),
        id="station_sync",
        replace_existing=True,
        # next_run_time=datetime.now(timezone.utc),  # run immediately on startup
    )
    scheduler.start()
    asyncio.get_event_loop().create_task(sync_now())
    logger.info(
        "Scheduler started - syncing every %d hours", settings.refresh_interval_hours
    )


def stop() -> None:
    scheduler.shutdown(wait=False)
