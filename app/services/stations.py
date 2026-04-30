import math
from typing import Optional
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.orm import Station, StationWasteType, StatusReport
from ..models.schemas import StationDetail, StationStatus, StationSummary, WasteTypeResponse
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


def _latest_status(db: Session, station_id: str) -> StationStatus:
    row = (
        db.query(StatusReport.status)
        .filter(StatusReport.station_id == station_id)
        .order_by(StatusReport.reported_at.desc())
        .first()
    )
    return StationStatus(row[0]) if row else StationStatus.unknown


def get_nearby(
    db: Session,
    lat: float,
    lon: float,
    limit: int,
    radius_km: float,
    categories: list[str],
    filter_mode: str,
) -> list[StationSummary]:
    min_lat, max_lat, min_lon, max_lon = _bbox(lat, lon, radius_km)

    q = db.query(Station).filter(
        Station.is_active == True,
        Station.latitude.between(min_lat, max_lat),
        Station.longitude.between(min_lon, max_lon),
    )

    if categories:
        cats = [c.lower().strip() for c in categories]
        if filter_mode == "all":
            q = q.filter(
                db.query(func.count(StationWasteType.waste_type))
                .filter(
                    StationWasteType.station_id == Station.id,
                    StationWasteType.waste_type.in_(cats),
                )
                .correlate(Station)
                .scalar_subquery()
                == len(cats)
            )
        else:
            q = (
                q.join(Station.waste_types)
                .filter(StationWasteType.waste_type.in_(cats))
                .distinct()
            )

    results: list[tuple[float, StationSummary]] = []
    for s in q.all():
        dist = _haversine(lat, lon, s.latitude, s.longitude)
        if dist > radius_km:
            continue
        results.append(
            (
                dist,
                StationSummary(
                    id=s.id,
                    name=s.name,
                    latitude=s.latitude,
                    longitude=s.longitude,
                    distance_km=round(dist, 3),
                    waste_types=[WasteTypeResponse.model_validate(wt) for wt in s.waste_types],
                    reported_status=_latest_status(db, s.id),
                    address=s.address,
                ),
            )
        )

    results.sort(key=lambda x: x[0])
    return [s for _, s in results[:limit]]


def get_by_id(db: Session, station_id: str) -> StationDetail:
    s = db.get(Station, station_id)
    if not s:
        raise HTTPException(404, f"Station '{station_id}' not found")

    return StationDetail(
        id=s.id,
        name=s.name,
        latitude=s.latitude,
        longitude=s.longitude,
        waste_types=[WasteTypeResponse.model_validate(wt) for wt in s.waste_types],
        reported_status=_latest_status(db, s.id),
        address=s.address,
        municipality=s.municipality,
        opening_hours=s.opening_hours,
        operator=s.operator,
        last_synced=s.last_synced,
        report_count=db.query(StatusReport)
        .filter(StatusReport.station_id == s.id)
        .count(),
    )


def get_categories(db: Session) -> dict[str, int]:
    rows = (
        db.query(StationWasteType.waste_type, func.count().label("n"))
        .join(Station)
        .filter(Station.is_active == True)
        .group_by(StationWasteType.waste_type)
        .order_by(func.count().desc())
        .all()
    )
    return {r.waste_type: r.n for r in rows}


def add_report(
    db: Session,
    station_id: str,
    user_id: str,
    status: str,
    note: Optional[str],
) -> int:
    if not db.get(Station, station_id):
        raise HTTPException(404, f"Station '{station_id}' not found")
    db.add(
        StatusReport(station_id=station_id, user_id=user_id, status=status, note=note)
    )
    db.commit()
    return db.query(StatusReport).filter(StatusReport.station_id == station_id).count()
