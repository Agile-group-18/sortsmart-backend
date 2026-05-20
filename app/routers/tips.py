from fastapi import APIRouter, Response
from app.config import get_settings
from ..data.facts import eco_tips

router = APIRouter(prefix="/tips", tags=["Daily Tips"])
settings = get_settings()


@router.get("")
def get_tips(response: Response):
    response.headers["Cache-Control"] = settings.PUBLIC_CACHE
    return eco_tips
