from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..schemas import LatestProduction, ProductionMixShare, ProductionPoint
from ..zones import validate_zone

router = APIRouter(prefix="/production", tags=["production"])


@router.get("/types", response_model=list[str])
def list_production_types(zone: str | None = Query(None, description="Restrict to types seen in this zone.")):
    """Distinct production types currently present in the database (e.g. 'hydro', 'wind_onshore')."""
    if zone is not None:
        validate_zone(zone)

    query = """
        SELECT DISTINCT production_type
        FROM production_per_source
        {zone_filter}
        ORDER BY production_type
    """
    params = {}
    zone_filter = ""
    if zone is not None:
        zone_filter = "WHERE zone = %(zone)s"
        params["zone"] = zone

    with get_cursor() as cur:
        cur.execute(query.format(zone_filter=zone_filter), params)
        rows = cur.fetchall()

    return [row["production_type"] for row in rows]


@router.get("", response_model=list[ProductionPoint])
def get_production(
    zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones."),
    production_type: str | None = Query(None, description="Filter to a single production type, e.g. 'hydro'."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Raw production time series (MW), optionally filtered by zone, production type and time range."""
    if zone is not None:
        validate_zone(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT zone, timestamp_utc, production_type, quantity_mw
        FROM production_per_source
        WHERE timestamp_utc >= %(start)s AND timestamp_utc < %(end)s
        {zone_filter}
        {type_filter}
        ORDER BY zone, production_type, timestamp_utc
        LIMIT %(limit)s
    """
    params = {"start": start, "end": end, "limit": limit}
    zone_filter = ""
    if zone is not None:
        zone_filter = "AND zone = %(zone)s"
        params["zone"] = zone
    type_filter = ""
    if production_type is not None:
        type_filter = "AND production_type = %(production_type)s"
        params["production_type"] = production_type

    with get_cursor() as cur:
        cur.execute(query.format(zone_filter=zone_filter, type_filter=type_filter), params)
        rows = cur.fetchall()

    return [ProductionPoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestProduction])
def get_latest_production(zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones.")):
    """Most recent production quantity per zone and production type."""
    if zone is not None:
        validate_zone(zone)

    query = """
        SELECT DISTINCT ON (zone, production_type) zone, production_type, timestamp_utc, quantity_mw
        FROM production_per_source
        {zone_filter}
        ORDER BY zone, production_type, timestamp_utc DESC
    """
    params = {}
    zone_filter = ""
    if zone is not None:
        zone_filter = "WHERE zone = %(zone)s"
        params["zone"] = zone

    with get_cursor() as cur:
        cur.execute(query.format(zone_filter=zone_filter), params)
        rows = cur.fetchall()

    return [LatestProduction(**row) for row in rows]


@router.get("/mix", response_model=list[ProductionMixShare])
def get_production_mix(
    zone: str = Query(..., description="Zone code, e.g. NO1. Required — the mix is computed per zone."),
    days: int = Query(7, ge=1, le=365),
):
    """
    Production mix for a zone over the trailing N days: average output and
    percentage share per production type.
    """
    validate_zone(zone)

    query = """
        WITH avg_by_type AS (
            SELECT production_type, avg(quantity_mw) AS avg_quantity_mw
            FROM production_per_source
            WHERE zone = %(zone)s AND timestamp_utc >= now() - (%(days)s || ' days')::interval
            GROUP BY production_type
        )
        SELECT
            %(zone)s AS zone,
            production_type,
            avg_quantity_mw,
            CASE WHEN sum(avg_quantity_mw) OVER () > 0
                 THEN 100.0 * avg_quantity_mw / sum(avg_quantity_mw) OVER ()
                 ELSE 0
            END AS share_percent
        FROM avg_by_type
        ORDER BY avg_quantity_mw DESC
    """
    params = {"zone": zone, "days": days}

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [ProductionMixShare(**row) for row in rows]
