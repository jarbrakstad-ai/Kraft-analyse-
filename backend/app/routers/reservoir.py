from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..schemas import LatestReservoir, ReservoirPoint
from ..zones import validate_zone

router = APIRouter(prefix="/reservoir", tags=["reservoir"])


@router.get("", response_model=list[ReservoirPoint])
def get_reservoir_fill(
    zone: str | None = Query(None, description="Zone code, e.g. NO1, or 'NO' for the national aggregate. Omit for all zones."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 1 year ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(2000, ge=1, le=10000),
):
    """Weekly reservoir fill level (%), optionally filtered by zone and time range."""
    if zone is not None:
        validate_zone(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=365)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT zone, week_start_utc, fill_percent, capacity_gwh
        FROM reservoir_fill
        WHERE week_start_utc >= %(start)s AND week_start_utc < %(end)s
        {zone_filter}
        ORDER BY zone, week_start_utc
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

    return [ReservoirPoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestReservoir])
def get_latest_reservoir_fill():
    """Most recent fill level per zone (including the national 'NO' aggregate)."""
    query = """
        SELECT DISTINCT ON (zone) zone, week_start_utc, fill_percent
        FROM reservoir_fill
        ORDER BY zone, week_start_utc DESC
    """
    with get_cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return [LatestReservoir(**row) for row in rows]
