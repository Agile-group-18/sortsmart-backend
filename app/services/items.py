from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.orm import Item, Category
from ..models.schemas import (
    ItemCategory,
    ItemDetail,
    ItemSearchResponse,
    ItemSearchResult,
)

# Prefer linked category data, but fall back to scraped category fields.
def _resolve_category(db: Session, item: Item) -> ItemCategory | None:
    if item.category_id:
        cat = db.get(Category, item.category_id)

        if cat:
            return ItemCategory(
                id=cat.id,
                name=cat.name,
                image_url=cat.image_url,
            )

    if item.category_name:
        return ItemCategory(
            id=None,
            name=item.category_name,
            image_url=item.category_image_url,
        )

    return None


def get_all_items(db: Session) -> list[ItemDetail]:
    items = db.query(Item).order_by(Item.name).all()

    return [
        ItemDetail(
            slug=item.slug,
            name=item.name,
            category=_resolve_category(db, item),
            leave_at=item.leave_at,
            processing=item.processing,
            last_scraped=item.last_scraped,
        )
        for item in items
    ]

def search_items(db: Session, q: str) -> ItemSearchResponse:
    # Use lowercase similarity search so Swedish characters and casing are handled more consistently.
    query = q.lower()

    results = (
        db.query(Item, func.similarity(func.lower(Item.name), query).label("score"))
        .filter(func.lower(Item.name).op("%")(query))
        .order_by(func.similarity(func.lower(Item.name), query).desc())
        .all()
    )

    return ItemSearchResponse(
        total=len(results),
        results=[
            ItemSearchResult(
                slug=item.slug,
                name=item.name,
                category=_resolve_category(db, item),
                leave_at=item.leave_at,
                processing=item.processing,
                score=round(score, 3),
            )
            for item, score in results
        ],
    )

def get_item(db: Session, slug: str) -> ItemDetail | None:
    item = db.query(Item).filter(Item.slug == slug).first()

    if not item:
        return None

    return ItemDetail(
        slug=item.slug,
        name=item.name,
        category=_resolve_category(db, item),
        leave_at=item.leave_at,
        processing=item.processing,
        last_scraped=item.last_scraped,
    )