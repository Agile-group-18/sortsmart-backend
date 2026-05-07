from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models.schemas import ItemSearchResponse, ItemDetail
from app.services import items as svc

router = APIRouter(prefix="/items", tags=["Items"])
settings = get_settings()


@router.get("", response_model=list[ItemDetail])
def get_items(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = settings.PUBLIC_CACHE
    return svc.get_all_items(db)


@router.get("/search", response_model=ItemSearchResponse)
def search(
    response: Response,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = settings.PUBLIC_CACHE
    return svc.search_items(db, q)


@router.get("/{slug}", response_model=ItemDetail)
def get_item(slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = settings.PUBLIC_CACHE
    item = svc.get_item(db, slug)
    if not item:
        raise HTTPException(404, f"Item '{slug}' not found")
    return item