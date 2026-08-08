from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..schemas import DailyAverage, LatestPrice, PricePoint, ZoneInfo
from ..zones import VALID_ZONES, ZONE_NAMES

router = APIRouter(prefix="/prices", tags=["prices"])


def _validate_zone(zone: str) -> str:
    if zone not in VALID_ZONES:
        raise HTTPException(status_code=404, detail=f"Unknown zone '{zone}'. Valid zones: {VALID_ZONES}")
    return zone


@router.get("/zones", response_model=list[ZoneInfo])
def list_zones():
    """List all bidding zones available in the API."""
    return [ZoneInfo(code=code, name=name) for code, name in ZONE_NAMES.items()]


@router.get("", response_model=list[PricePoint])
def get_prices(
    zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Raw spot price time series, optionally filtered by zone and time range."""
    if zone is not None:
        _validate_zone(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT zone, timestamp_utc, price_eur_mwh, resolution_min
        FROM spot_price
        WHERE timestamp_utc >= %(start)s AND timestamp_utc < %(end)s
        {zone_filter}
        ORDER BY zone, timestamp_utc
        LIMIT %(limit)s
    """
    params = {"start": start, "end": end, "limit": limit}
    zone_filter = ""
    if zone is not None:
        zone_filter = "AND zone = %(zone)s"
        params["zone"] = zone

    with get_cursor() as cur:
        cur.execute(query.format(zone_filter=zone_filter), params)
        rows = cur.fetchall()

    return [PricePoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestPrice])
def get_latest_prices():
    """Most recent price point per zone."""
    query = """
        SELECT DISTINCT ON (zone) zone, timestamp_utc, price_eur_mwh
        FROM spot_price
        ORDER BY zone, timestamp_utc DESC
    """
    with get_cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return [LatestPrice(**row) for row in rows]


@router.get("/daily-average", response_model=list[DailyAverage])
def get_daily_average(
    zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones."),
    days: int = Query(7, ge=1, le=365),
):
    """Daily average/min/max price per zone over the trailing N days."""
    if zone is not None:
        _validate_zone(zone)

    query = """
        SELECT
            zone,
            date_trunc('day', timestamp_utc)::date AS day,
            avg(price_eur_mwh) AS avg_price_eur_mwh,
            min(price_eur_mwh) AS min_price_eur_mwh,
            max(price_eur_mwh) AS max_price_eur_mwh
        FROM spot_price
        WHERE timestamp_utc >= now() - (%(days)s || ' days')::interval
        {zone_filter}
        GROUP BY zone, day
        ORDER BY zone, day
    """
    params = {"days": days}
    zone_filter = ""
    if zone is not None:
        zone_filter = "AND zone = %(zone)s"
        params["zone"] = zone

    with get_cursor() as cur:
        cur.execute(query.format(zone_filter=zone_filter), params)
        rows = cur.fetchall()

    return [DailyAverage(**row) for row in rows]
