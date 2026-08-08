from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..interconnectors import INTERCONNECTORS, validate_interconnector
from ..schemas import FlowDailyAverage, FlowPoint, InterconnectorInfo, LatestFlow
from ..zones import validate_zone

router = APIRouter(prefix="/flow", tags=["flow"])


@router.get("/interconnectors", response_model=list[InterconnectorInfo])
def list_interconnectors():
    """List the interconnectors (utenlandskabler) tracked by the API."""
    return [InterconnectorInfo(name=name, from_zone=a, to_zone=b) for name, (a, b) in INTERCONNECTORS.items()]


@router.get("", response_model=list[FlowPoint])
def get_flow(
    from_zone: str | None = Query(None, description="Sending zone, e.g. NO2."),
    to_zone: str | None = Query(None, description="Receiving zone, e.g. NL."),
    interconnector: str | None = Query(None, description="Interconnector name, e.g. 'NorNed'."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Raw cross-border flow time series (MW), optionally filtered by zone pair, interconnector and time range."""
    if from_zone is not None:
        validate_zone(from_zone)
    if to_zone is not None:
        validate_zone(to_zone)
    if interconnector is not None:
        validate_interconnector(interconnector)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT from_zone, to_zone, interconnector, timestamp_utc, flow_mw
        FROM cross_border_flow
        WHERE timestamp_utc >= %(start)s AND timestamp_utc < %(end)s
        {from_filter} {to_filter} {interconnector_filter}
        ORDER BY from_zone, to_zone, timestamp_utc
        LIMIT %(limit)s
    """
    params = {"start": start, "end": end, "limit": limit}
    from_filter = ""
    if from_zone is not None:
        from_filter = "AND from_zone = %(from_zone)s"
        params["from_zone"] = from_zone
    to_filter = ""
    if to_zone is not None:
        to_filter = "AND to_zone = %(to_zone)s"
        params["to_zone"] = to_zone
    interconnector_filter = ""
    if interconnector is not None:
        interconnector_filter = "AND interconnector = %(interconnector)s"
        params["interconnector"] = interconnector

    with get_cursor() as cur:
        cur.execute(query.format(from_filter=from_filter, to_filter=to_filter, interconnector_filter=interconnector_filter), params)
        rows = cur.fetchall()

    return [FlowPoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestFlow])
def get_latest_flow(interconnector: str | None = Query(None, description="Interconnector name, e.g. 'NorNed'.")):
    """Most recent flow point per zone-pair direction."""
    if interconnector is not None:
        validate_interconnector(interconnector)

    query = """
        SELECT DISTINCT ON (from_zone, to_zone) from_zone, to_zone, interconnector, timestamp_utc, flow_mw
        FROM cross_border_flow
        {interconnector_filter}
        ORDER BY from_zone, to_zone, timestamp_utc DESC
    """
    params = {}
    interconnector_filter = ""
    if interconnector is not None:
        interconnector_filter = "WHERE interconnector = %(interconnector)s"
        params["interconnector"] = interconnector

    with get_cursor() as cur:
        cur.execute(query.format(interconnector_filter=interconnector_filter), params)
        rows = cur.fetchall()

    return [LatestFlow(**row) for row in rows]


@router.get("/daily-average", response_model=list[FlowDailyAverage])
def get_daily_average_flow(
    interconnector: str | None = Query(None, description="Interconnector name, e.g. 'NorNed'."),
    days: int = Query(7, ge=1, le=365),
):
    """Daily average flow (MW) per zone-pair direction over the trailing N days."""
    if interconnector is not None:
        validate_interconnector(interconnector)

    query = """
        SELECT
            from_zone,
            to_zone,
            max(interconnector) AS interconnector,
            date_trunc('day', timestamp_utc)::date AS day,
            avg(flow_mw) AS avg_flow_mw
        FROM cross_border_flow
        WHERE timestamp_utc >= now() - (%(days)s || ' days')::interval
        {interconnector_filter}
        GROUP BY from_zone, to_zone, day
        ORDER BY from_zone, to_zone, day
    """
    params = {"days": days}
    interconnector_filter = ""
    if interconnector is not None:
        interconnector_filter = "AND interconnector = %(interconnector)s"
        params["interconnector"] = interconnector

    with get_cursor() as cur:
        cur.execute(query.format(interconnector_filter=interconnector_filter), params)
        rows = cur.fetchall()

    return [FlowDailyAverage(**row) for row in rows]
