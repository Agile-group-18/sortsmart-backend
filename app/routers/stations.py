from typing import Annotated, Optional
from urllib import response
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
    StationView,
    StationsResponse,
)
from ..models.orm import User
from ..services import stations as svc
from ..core.deps import get_verified_user
from ..config import get_settings

router = APIRouter(prefix="/stations", tags=["Stations"])
settings = get_settings()


@router.get("/categories", response_model=list[CategoryResponse])
def categories(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.categories_cache_seconds}"
    )
    return svc.get_categories(db)


@router.get("", response_model=NearbyResponse | StationsResponse)
def get_stations(
    response: Response,
    lat: Annotated[Optional[float], Query(ge=-90, le=90)] = None,
    lon: Annotated[Optional[float], Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float, Query(ge=0.1, le=500)] = settings.default_radius_km,
    category_ids: Annotated[list[int], Query()] = [],
    filter_mode: FilterMode = FilterMode.any,
    station_type: Optional[str] = None,
    view: StationView = StationView.map,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.nearby_cache_seconds}"
    )
    stations = svc.get_stations(
        db,
        lat,
        lon,
        radius_km,
        category_ids,
        filter_mode.value,
        station_type,
        view.value,
    )
    if lat is not None and lon is not None:
        return NearbyResponse(
            total=len(stations), stations=stations, query_lat=lat, query_lon=lon
        )
    return StationsResponse(total=len(stations), stations=stations)


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
        db, station_id, current_user.id, body.category_id, body.status.value, body.note
    )
    return ReportResponse(
        station_id=station_id,
        status=body.status,
        report_count=count,
        message="Report recorded - thank you!",
    )
