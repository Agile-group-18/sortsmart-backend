import logging
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


async def sync_now(db: Session | None = None) -> None:
    """Run a full station sync. Pass an existing db session or None to create one."""
    global _next_run
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        stations = await fetch_all()
        if not stations:
            logger.warning(
                "Fetch returned 0 stations - aborting upsert to preserve existing data"
            )
            return

        unique: dict[str, Station] = {s.id: s for s in stations}

        for s in unique.values():
            existing = db.get(Station, s.id)
            if existing:
                existing.name = s.name
                existing.latitude = s.latitude
                existing.longitude = s.longitude
                existing.address = s.address
                existing.municipality = s.municipality
                existing.opening_hours = s.opening_hours
                existing.operator = s.operator
                existing.is_active = True
                existing.last_synced = s.last_synced
                # Replace waste types
                db.query(StationWasteType).filter(
                    StationWasteType.station_id == s.id
                ).delete()
                for wt in s.waste_types:
                    db.add(
                        StationWasteType(
                            station_id=s.id,
                            waste_type=wt.waste_type,
                            image_url=wt.image_url,
                        )
                    )
            else:
                db.add(s)

        # Soft-delete stations no longer in the API (preserves historical reports)
        live_ids = set(unique.keys())
        db.query(Station).filter(Station.id.notin_(live_ids)).update(
            {"is_active": False}
        )

        # Update sync metadata
        meta = db.get(SyncMeta, 1) or SyncMeta(id=1)
        meta.last_sync = datetime.now(timezone.utc)
        meta.station_count = len(unique)
        db.add(meta)

        db.commit()
        _next_run = datetime.now(timezone.utc) + timedelta(
            hours=settings.refresh_interval_hours
        )
        logger.info("Sync done - %d stations. Next run: %s", len(unique), _next_run)

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
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    logger.info(
        "Scheduler started - syncing every %d hours", settings.refresh_interval_hours
    )


def stop() -> None:
    scheduler.shutdown(wait=False)
