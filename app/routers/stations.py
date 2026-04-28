from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schemas import (
    NearbyResponse,
    StationDetail,
    CategoryResponse,
    ReportRequest,
    ReportResponse,
    FilterMode,
)
from ..models.orm import User
from ..services import stations as svc
from ..core.deps import get_verified_user
from ..config import get_settings

router = APIRouter(prefix="/stations", tags=["Stations"])
settings = get_settings()


@router.get("/categories", response_model=CategoryResponse)
def categories(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.categories_cache_seconds}"
    )
    cats = svc.get_categories(db)
    return CategoryResponse(categories=list(cats), total_stations_per_category=cats)


@router.get("", response_model=NearbyResponse)
def nearby(
    response: Response,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    limit: Annotated[
        int, Query(ge=1, le=settings.max_nearby_limit)
    ] = settings.default_nearby_limit,
    radius_km: Annotated[float, Query(ge=0.1, le=500)] = settings.default_radius_km,
    categories: Annotated[list[str], Query()] = [],
    filter_mode: FilterMode = FilterMode.any,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.nearby_cache_seconds}"
    )
    stations = svc.get_nearby(
        db, lat, lon, limit, radius_km, categories, filter_mode.value
    )
    return NearbyResponse(
        total=len(stations), stations=stations, query_lat=lat, query_lon=lon
    )


@router.get("/{station_id}", response_model=StationDetail)
def detail(station_id: str, db: Session = Depends(get_db)):
    return svc.get_by_id(db, station_id)


@router.post("/{station_id}/report", response_model=ReportResponse, status_code=201)
def report(
    station_id: str,
    body: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    count = svc.add_report(
        db, station_id, current_user.id, body.status.value, body.note
    )
    return ReportResponse(
        station_id=station_id,
        status=body.status,
        report_count=count,
        message="Report recorded - thank you!",
    )
