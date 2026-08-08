from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..schemas import ConsumptionPoint, LatestConsumption
from ..zones import validate_zone

router = APIRouter(prefix="/consumption", tags=["consumption"])


@router.get("", response_model=list[ConsumptionPoint])
def get_consumption(
    zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Raw actual total load (consumption) time series (MW), optionally filtered by zone and time range."""
    if zone is not None:
        validate_zone(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT zone, timestamp_utc, load_mw
        FROM consumption
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

    return [ConsumptionPoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestConsumption])
def get_latest_consumption():
    """Most recent load point per zone."""
    query = """
        SELECT DISTINCT ON (zone) zone, timestamp_utc, load_mw
        FROM consumption
        ORDER BY zone, timestamp_utc DESC
    """
    with get_cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return [LatestConsumption(**row) for row in rows]
