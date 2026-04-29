import asyncio, logging, httpx
from datetime import datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup

from .config import get_settings
from .models.orm import Station, StationWasteType

settings = get_settings()
logger = logging.getLogger("sortsmart.fetcher")

AVFALLSHUBBEN_URL = (
    "https://avfallshubben.avfallsverige.se/umbraco/Api/SoporApi/GetCacheItems/"
)
SOPOR_DETAIL_URL = "https://www.sopor.nu/umbraco/surface/AvfallshubbenSurface/GetItem/"
CONCURRENCY = 15


def _parse_avs(raw: dict[str, Any]) -> Station | None:
    try:
        s = Station(
            id=str(raw["id"]),
            name=(raw.get("name") or "Unknown").strip(),
            latitude=float(raw["lat"]),
            longitude=float(raw["long"]),
            address=raw.get("streetAddress"),
            municipality=raw.get("municipalityCode"),
            opening_hours=None,
            operator=None,
            station_type="avs",
            external_id=str(raw.get("externalAvsId", "")),
            is_active=True,
            last_synced=datetime.now(timezone.utc),
        )
        s.waste_types = []
        return s
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Skipping AVS id=%s: %s", raw.get("id"), exc)
        return None


def _parse_avc(raw: dict[str, Any]) -> Station | None:
    try:
        s = Station(
            id=str(raw["id"]),
            name=(raw.get("name") or "Unknown").strip(),
            latitude=float(raw["lat"]),
            longitude=float(raw["long"]),
            address=raw.get("streetAddress"),
            municipality=raw.get("municipalityCode"),
            opening_hours=raw.get("openingHours") or raw.get("openingHoursUrl"),
            operator=None,
            station_type="avc",
            external_id=raw.get("externalAvcId"),
            is_active=True,
            last_synced=datetime.now(timezone.utc),
        )
        fractions: list[Any] = raw.get("fractions") or []
        s.waste_types = [
            StationWasteType(station_id=s.id, waste_type=str(f).strip())
            for f in fractions
            if f
        ]
        return s
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Skipping AVC id=%s: %s", raw.get("id"), exc)
        return None


def _parse_waste_types_html(html: str, station_id: str) -> list[StationWasteType]:
    soup = BeautifulSoup(html, "html.parser")
    icon_list = soup.find("li", class_="icon-list")
    if not icon_list:
        return []
    waste_types = []
    for row in icon_list.find_all("li"):
        image_tag = row.find("img")
        name_tag = row.find("strong")
        
        if name_tag:
            name = name_tag.get_text(strip=True)
            image_url = None
            if image_tag:
                image_url = "https://www.sopor.nu" + image_tag.get("src")
            waste_types.append(StationWasteType(station_id, name, image_url))
    return waste_types


async def _enrich_avx(
    client: httpx.AsyncClient,
    station: Station,
    semaphore: asyncio.Semaphore,
    type: int = 0,
) -> None:

    if not station.external_id or not station.municipality:
        return
    async with semaphore:
        try:
            resp = await client.get(
                SOPOR_DETAIL_URL,
                params={
                    "externalId": station.external_id,
                    "municipalityCode": station.municipality,
                    "type": type,
                },
            )
            resp.raise_for_status()
            station.waste_types = _parse_waste_types_html(resp.text, station.id)
        except Exception as exc:
            logger.warning(
                "Failed to enrich AVS %s (extId=%s): %s",
                station.id,
                station.external_id,
                exc,
            )


async def fetch_all() -> list[Station]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        logger.info("Fetching station list from avfallshubben...")
        resp = await client.get(AVFALLSHUBBEN_URL)
        resp.raise_for_status()
        data = resp.json()

        avs_stations: list[Station] = [
            s for raw in data.get("avsList", []) if (s := _parse_avs(raw)) is not None
        ]
        avc_stations: list[Station] = [
            s for raw in data.get("avcList", []) if (s := _parse_avc(raw)) is not None
        ]
        logger.info(
            "Parsed %d AVS + %d AVC stations", len(avs_stations), len(avc_stations)
        )

        logger.info("Enriching AVS stations with waste types from sopor.nu...")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        await asyncio.gather(
            *[_enrich_avx(client, s, semaphore, 0) for s in avs_stations]
        )
        await asyncio.gather(
            *[_enrich_avx(client, s, semaphore, 1) for s in avc_stations]
        )

        enriched_avs = sum(1 for s in avs_stations if s.waste_types)
        logger.info("Enriched %d/%d AVS stations", enriched_avs, len(avs_stations))
        enriched_avc = sum(1 for s in avc_stations if s.waste_types)
        logger.info("Enriched %d/%d AVC stations", enriched_avc, len(avc_stations))

    all_stations = avs_stations + avc_stations
    logger.info("Total: %d stations", len(all_stations))
    return all_stations
