from fastapi import APIRouter
from app.services.items import search_items

router = APIRouter(prefix="/items", tags=["Items"])

@router.get("/search")
def search(q: str):
    return search_items(q)