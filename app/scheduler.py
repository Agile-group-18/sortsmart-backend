import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from .config import get_settings
from .database import SessionLocal
from .fetcher_station import fetch_all
from .fetcher_item import fetch_all_items
from .models.orm import Station, StationCategory, Category, StatusReport, SyncMeta, User, Item

settings = get_settings()
logger = logging.getLogger("sortsmart.scheduler")
scheduler = AsyncIOScheduler()
_next_run: datetime | None = None
_next_item_run: datetime | None = None


async def sync_stations(db: Session | None = None) -> None:
    """Run a full station sync. Pass an existing db session or None to create one."""
    global _next_run
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    meta = db.get(SyncMeta, 1)
    if meta is not None and meta.last_sync is not None:
        last_sync = meta.last_sync
        if last_sync and datetime.now(timezone.utc) - last_sync.astimezone(
            timezone.utc
        ) < timedelta(minutes=30):
            logger.info("Last sync was less than %d minutes ago - skipping", 30)
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
            elif image_url and cat.image_url != image_url:
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


async def sync_items(db: Session | None = None) -> None:
    """Run a full item sync from sopor.nu."""
    global _next_item_run
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        items = await fetch_all_items()
        if not items:
            logger.warning("fetch_all_items returned 0 items - aborting")
            return

        for item in items:
            detail: dict = getattr(item, "_raw_detail", None)  # type: ignore

            existing = db.get(Item, item.slug)
            if existing:
                existing.name = item.name
                existing.last_scraped = item.last_scraped
            else:
                existing = item
                db.add(existing)
            db.flush()

            if not detail:
                continue

            # Try to match category to DB
            cat_name = detail.get("category_name")
            cat = (
                db.query(Category).filter(Category.name.ilike(cat_name)).first()
                if cat_name
                else None
            )

            if cat:
                existing.category_id = cat.id
                existing.category_name = None
                existing.category_image_url = None
            else:
                existing.category_id = None
                existing.category_name = cat_name
                existing.category_image_url = detail.get("category_image_url")

            existing.leave_at = detail.get("leave_at")
            existing.processing = detail.get("processing", "")

        db.commit()
        _next_item_run = datetime.now(timezone.utc) + timedelta(days=30)
        logger.info(
            "Item sync done - %d items. Next run: %s", len(items), _next_item_run
        )

    except Exception as exc:
        logger.error("Item sync failed: %s", exc, exc_info=True)
        if owns_session:
            db.rollback()
    finally:
        if owns_session:
            db.close()


async def clear_disabled_accounts(db: Session | None = None) -> None:
    """Permanently delete accounts disabled for over 90 days."""
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        deleted = (
            db.query(User)
            .filter(
                ~User.is_active,
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

async def clear_expired_reports(db: Session | None = None) -> None:
    """Permanently delete status reports older than 3 days."""
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        expire_limit = datetime.now(timezone.utc) - timedelta(days=3)
        deleted = (
            db.query(StatusReport)
            .filter(StatusReport.reported_at < expire_limit)
            .delete()
        )
        db.commit()
        logger.info("Deleted %d expired status reports", deleted)
    except Exception as exc:
        logger.error("Failed to clear expired reports: %s", exc, exc_info=True)
        if owns_session:
            db.rollback()
    finally:
        if owns_session:
            db.close()

def get_next_run() -> datetime | None:
    return _next_run


def get_next_item_run() -> datetime | None:
    return _next_item_run


def start() -> None:
    scheduler.add_job(
        sync_stations,
        trigger=IntervalTrigger(days=settings.refresh_interval_days),
        id="station_sync",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        sync_items,
        trigger=IntervalTrigger(days=settings.refresh_interval_days),
        id="item_sync",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        clear_disabled_accounts,
        trigger=IntervalTrigger(days=90),
        id="clear_disabled_accounts",
        replace_existing=True,
    )
    scheduler.add_job(
        clear_expired_reports,
        trigger=IntervalTrigger(days=1), 
        id="clear_expired_reports",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    logger.info(
        "Scheduler started - syncing stations every %d days, items every %d days",
        settings.refresh_interval_days,
        settings.refresh_interval_days
    )


def stop() -> None:
    scheduler.shutdown(wait=False)
