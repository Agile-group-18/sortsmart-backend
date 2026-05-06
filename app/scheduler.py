import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from .config import get_settings
from .database import SessionLocal
from .fetcher import fetch_all
from .models.orm import Station, StationCategory, Category, SyncMeta, User

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

    meta = db.get(SyncMeta, 1)
    if meta is not None:
        last_sync = meta.last_sync
        if last_sync and datetime.now(timezone.utc) - last_sync.astimezone(timezone.utc) < timedelta(
            days=settings.refresh_interval_days
        ):
            logger.info(
                "Last sync was less than %d days ago - skipping",
                settings.refresh_interval_days,
            )
            return
    logger.debug(
        "Starting station sync - last sync was at %s",
        meta.last_sync if meta else "never",
    )
    try:
        stations = await fetch_all()
        if not stations:
            logger.warning(
                "Fetch returned 0 stations - aborting upsert to preserve existing data"
            )
            return

        unique: dict[str, Station] = {s.id: s for s in stations}

        all_raw: dict[str, str | None] = {}
        for s in unique.values():
            for c in getattr(s, "_raw_categories", []):
                if c["name"] not in all_raw or (
                    c["image_url"] and not all_raw[c["name"]]
                ):
                    all_raw[c["name"]] = c["image_url"]

        name_to_id: dict[str, int] = {}
        for name, image_url in all_raw.items():
            cat = db.query(Category).filter_by(name=name).first()
            if not cat:
                cat = Category(name=name, image_url=image_url)
                db.add(cat)
                db.flush()
            elif image_url and not cat.image_url:
                cat.image_url = image_url
            name_to_id[name] = cat.id

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
                existing.external_id = s.external_id
                existing.station_type = s.station_type
                existing.is_active = True
                existing.last_synced = s.last_synced
            else:
                db.add(s)
            db.flush()

            db.query(StationCategory).filter_by(station_id=s.id).delete()
            for raw_cat in getattr(s, "_raw_categories", []):
                cat_id = name_to_id.get(raw_cat["name"])
                if cat_id:
                    db.add(StationCategory(station_id=s.id, category_id=cat_id))

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
            days=settings.refresh_interval_days
        )
        logger.info("Sync done - %d stations. Next run: %s", len(unique), _next_run)

    except Exception as exc:
        logger.error("Sync failed: %s", exc, exc_info=True)
        if owns_session:
            db.rollback()
    finally:
        if owns_session:
            db.close()


async def clear_disabled_accounts(db: Session | None = None) -> None:
    """Permanently delete accounts that have been disabled for a long time. Pass an existing db session or None to create one."""
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        deleted = (
            db.query(User)
            .filter(
                User.is_active == False,
                User.updated_at < datetime.now(timezone.utc) - timedelta(days=90),
            )
            .delete()
        )
        db.commit()
        logger.info("Deleted %d disabled accounts", deleted)
    except Exception as exc:
        logger.error("Failed to clear accounts: %s", exc, exc_info=True)
        db.rollback()
    finally:
        if owns_session:
            db.close()


def get_next_run() -> datetime | None:
    return _next_run


def start() -> None:
    """Start the scheduler and add jobs."""
    scheduler.add_job(
        sync_now,
        trigger=IntervalTrigger(days=settings.refresh_interval_days),
        id="station_sync",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.add_job(
        clear_disabled_accounts,
        trigger=IntervalTrigger(days=90),
        id="clear_disabled_accounts",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started - syncing every %d days", settings.refresh_interval_days
    )


def stop() -> None:
    """Stop the scheduler and all running jobs."""
    scheduler.shutdown(wait=False)
