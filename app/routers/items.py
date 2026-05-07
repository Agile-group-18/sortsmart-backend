from fastapi import APIRouter, Response
from app.config import get_settings
from app.services.items import search_items

router = APIRouter(prefix="/items", tags=["Items"])
settings = get_settings()


@router.get("/search")
def search(response: Response, q: str):
    response.headers["Cache-Control"] = settings.PUBLIC_CACHE
    return search_items(q)
