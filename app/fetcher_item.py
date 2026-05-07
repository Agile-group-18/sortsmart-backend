import asyncio, logging, re, httpx
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from .config import get_settings
from .models.orm import Item

settings = get_settings()
logger = logging.getLogger("sortsmart.fetcher_items")

SOPOR_ITEM_LIST_URL = "https://www.sopor.nu/umbraco/api/AutocompleteApi/GetStrings"
SOPOR_SCRAPE_URL = "https://www.sopor.nu/haer-aatervinner-du/"
CONCURRENCY = 15


def _slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[åä]", "a", name)
    name = re.sub(r"ö", "o", name)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def _parse_item(name: str) -> Item | None:
    try:
        return Item(
            name=name.strip(),
            slug=_slugify(name),
            last_scraped=datetime.now(timezone.utc),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Skipping item name=%s: %s", name, exc)
        return None


def _parse_item_html(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    result = soup.find("div", class_="recycleSearchResult")
    if not result:
        return None

    # category name + image — "Sorteras som" column
    cols = result.select(".row > div")
    if len(cols) < 3:
        return None

    sorteras_col = cols[0]
    category_strong = sorteras_col.find("strong")
    category_name = category_strong.get_text(strip=True) if category_strong else None

    img_tag = result.find("img")
    src = img_tag.get("src") if img_tag else None
    category_image_url = (
        f"https://www.sopor.nu{src}" if src and src.startswith("/") else src # type: ignore
    )

    # leave_at — "Lämnas" column
    lamnas_col = cols[1]
    lamnas_strong = lamnas_col.find("strong")
    leave_at = lamnas_strong.get_text(strip=True) if lamnas_strong else None

    # processing — "Behandling" column
    behandling_col = cols[2]
    behandling_strong = behandling_col.find("strong")
    processing = behandling_strong.get_text(strip=True) if behandling_strong else ""

    return {
        "category_name": category_name,
        "category_image_url": category_image_url,
        "leave_at": leave_at,
        "processing": processing or "",
    }


async def _enrich_item(
    client: httpx.AsyncClient, item: Item, semaphore: asyncio.Semaphore
) -> None:
    async with semaphore:
        try:
            resp = await client.get(
                SOPOR_SCRAPE_URL,
                params={
                    "searchTerm": item.name,
                    "lang": "sv-se",
                    "pageSize": 1,
                    "page": 0,
                },
            )
            resp.raise_for_status()
            parsed = _parse_item_html(resp.text)
            if parsed:
                item._raw_detail = parsed  # type: ignore
        except Exception as exc:
            logger.warning("Failed to enrich item %s: %s", item.name, exc)


async def fetch_all_items() -> list[Item]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        logger.info("Fetching item list from sopor.nu...")
        resp = await client.get(SOPOR_ITEM_LIST_URL, params={"culture": "sv-se"})
        resp.raise_for_status()
        data = resp.json()

        items: list[Item] = [s for name in data if (s := _parse_item(name)) is not None]
        logger.info("Parsed %d items", len(items))

        semaphore = asyncio.Semaphore(CONCURRENCY)
        await asyncio.gather(*[_enrich_item(client, s, semaphore) for s in items])

        enriched = sum(1 for s in items if hasattr(s, "_raw_detail"))
        logger.info("Enriched %d/%d items", enriched, len(items))

    return items
