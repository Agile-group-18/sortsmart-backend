import math
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, tuple_
from ..models.orm import Station, StationCategory, Category, StatusReport
from ..models.schemas import (
    StationDetail,
    StationStatus,
    StationMapItem,
    StationListItem,
    CategoryResponse,
    CategoryStatusResponse,
)
from ..config import get_settings

settings = get_settings()


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _bbox(lat: float, lon: float, km: float):
    dlat = km / 111.0
    dlon = km / (111.0 * math.cos(math.radians(lat)))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


def _category_statuses(db: Session, station_id: str) -> list[CategoryStatusResponse]:
    """[DEPRECATED] Get the latest report status per category for a station."""
    cats = (
        db.query(StationCategory.category_id)
        .filter(StationCategory.station_id == station_id)
        .all()
    )
    problem_cats = (
        db.query(StatusReport.category_id)
        .filter(
            StatusReport.station_id == station_id,
            StatusReport.status.in_(["full", "not_working"])
        )
        .group_by(StatusReport.category_id)
        .having(func.count(StatusReport.id) >= 3)
        .all()
    )
    
    problem_cat_ids = {row[0] for row in problem_cats}

    result = []
    for (cat_id,) in cats:
        status = StationStatus.full if cat_id in problem_cat_ids else StationStatus.operational
        
        result.append(
            CategoryStatusResponse(
                id=cat_id,
                status=status,
            )
        )
    return result


def _bulk_category_statuses(
    db: Session, station_ids: list[str]
) -> dict[str, list[CategoryStatusResponse]]:
    if not station_ids:
        return {}

    problem_pairs = (
        db.query(StatusReport.station_id, StatusReport.category_id)
        .filter(
            StatusReport.station_id.in_(station_ids),
            StatusReport.status.in_(["full", "not_working"])
        )
        .group_by(StatusReport.station_id, StatusReport.category_id)
        .having(func.count(StatusReport.id) >= 3)
        .all()
    )

    problem_set = {(row[0], row[1]) for row in problem_pairs}

    sc_rows = (
        db.query(StationCategory.station_id, StationCategory.category_id)
        .filter(StationCategory.station_id.in_(station_ids))
        .all()
    )

    result: dict[str, list[CategoryStatusResponse]] = {}
    for station_id, category_id in sc_rows:
        is_problem = (station_id, category_id) in problem_set
        status = StationStatus.full if is_problem else StationStatus.operational

        result.setdefault(station_id, []).append(
            CategoryStatusResponse(
                id=category_id,
                status=status,
            )
        )
    return result


def _build_list_item(
    db: Session, s: Station, distance_km: Optional[float] = None
) -> StationListItem:
    return StationListItem(
        id=s.id,
        name=s.name,
        latitude=s.latitude,
        longitude=s.longitude,
        address=s.address,
        municipality=s.municipality,
        station_type=s.station_type,
        opening_hours=s.opening_hours,
        operator=s.operator,
        distance_km=distance_km,
        categories=[
            CategoryResponse(
                id=sc.category.id,
                name=sc.category.name,
                image_url=sc.category.image_url,
            )
            for sc in s.station_categories
        ],
        last_synced=s.last_synced,
    )


def _build_map_item(s: Station, statuses: dict, distance_km: Optional[float] = None) -> StationMapItem:
    stationMap = StationMapItem(
        id=s.id,
        station_type=s.station_type,
        latitude=s.latitude,
        longitude=s.longitude,
        categories=statuses.get(s.id, [])
    )
    
    if distance_km is not None:
        stationMap.distance_km = distance_km
        
    return stationMap


def _base_query(db: Session, category_ids: list[int], filter_mode: str):
    q = db.query(Station).filter(Station.is_active == True)
    if category_ids:
        if filter_mode == "all":
            q = q.filter(
                db.query(func.count(StationCategory.category_id))
                .filter(
                    StationCategory.station_id == Station.id,
                    StationCategory.category_id.in_(category_ids),
                )
                .correlate(Station)
                .scalar_subquery()
                == len(category_ids)
            )
        else:
            q = (
                q.join(Station.station_categories)
                .filter(StationCategory.category_id.in_(category_ids))
                .distinct()
            )
    return q


def get_stations(
    db: Session,
    lat: Optional[float],
    lon: Optional[float],
    radius_km: float,
    category_ids: list[int],
    filter_mode: str,
    station_type: Optional[str],
    view: str,
) -> list[StationMapItem | StationListItem]:
    q = _base_query(db, category_ids, filter_mode)

    if station_type:
        q = q.filter(Station.station_type == station_type)

    if view == "list":
        q = q.options(
            selectinload(Station.station_categories).joinedload(StationCategory.category) # one to many + many to one, therefore, two queries instead of one big join (which would cause duplicates)
        )

    stations = q.all()
    station_ids = [s.id for s in stations]

    if lat is not None and lon is not None:
        min_lat, max_lat, min_lon, max_lon = _bbox(lat, lon, radius_km)
        results: list[tuple[float, Station]] = []

        for s in stations:
            if not (
                min_lat <= s.latitude <= max_lat and min_lon <= s.longitude <= max_lon
            ):
                continue

            dist = _haversine(lat, lon, s.latitude, s.longitude)
            if dist <= radius_km:
                results.append((dist, s))

        results.sort(key=lambda x: x[0])
        if view == "map":
            # keep statuses only when needed
            statuses = _bulk_category_statuses(db, station_ids)
            return [_build_map_item(s, statuses, round(dist, 3)) for dist, s in results]
        return [_build_list_item(db, s, round(dist, 3)) for dist, s in results]

    if view == "list":
        return [_build_list_item(db, s) for s in stations]

    # keep statuses only when needed
    statuses = _bulk_category_statuses(db, station_ids)
    return [_build_map_item(s, statuses) for s in stations]


def get_by_id(db: Session, station_id: str) -> StationDetail:
    s = (
        db.query(Station)
        .options(
            selectinload(Station.station_categories).joinedload(StationCategory.category)
        )
        .filter(Station.id == station_id)
        .first()
    )
    if not s:
        raise HTTPException(404, f"Station '{station_id}' not found")

    return StationDetail(
        id=s.id,
        name=s.name,
        latitude=s.latitude,
        longitude=s.longitude,
        address=s.address,
        municipality=s.municipality,
        station_type=s.station_type,
        opening_hours=s.opening_hours,
        operator=s.operator,
        categories=_category_statuses(db, s.id),
        report_count=db.query(StatusReport)
        .filter(StatusReport.station_id == s.id)
        .count(),
        last_synced=s.last_synced,
    )



def get_categories(db: Session) -> list[CategoryResponse]:
    cats = db.query(Category).order_by(Category.name).all()
    return [CategoryResponse(id=c.id, name=c.name, image_url=c.image_url) for c in cats]


def add_report(
    db: Session,
    station_id: str,
    user_id: str,
    category_id: int,
    status: str,
    note: Optional[str],
) -> int:
    if not db.get(Station, station_id):
        raise HTTPException(404, f"Station '{station_id}' not found")
    if not db.get(Category, category_id):
        raise HTTPException(404, f"Category '{category_id}' not found")
    
    existing_report = (db.query(StatusReport).filter(
        StatusReport.station_id == station_id,
        StatusReport.user_id == user_id,
        StatusReport.category_id == category_id
        ).first()
    )
    if existing_report:
        raise HTTPException(400, "You have already submitted a report for this station and category")

    db.add(
        StatusReport(
            station_id=station_id,
            user_id=user_id,
            category_id=category_id,
            status=status,
            note=note,
        )
    )
    db.commit()

    return db.query(StatusReport).filter(StatusReport.station_id == station_id).count()
