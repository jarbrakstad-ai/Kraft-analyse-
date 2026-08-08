from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..schemas import LatestWeather, WeatherPoint
from ..zones import validate_zone

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", response_model=list[WeatherPoint])
def get_weather(
    zone: str | None = Query(None, description="Zone code, e.g. NO1. Omit for all zones."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Raw hourly weather observations (temperature, wind speed, precipitation), optionally filtered by zone and time range."""
    if zone is not None:
        validate_zone(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        SELECT zone, station_id, timestamp_utc, temperature_c, wind_speed_ms, precipitation_mm
        FROM weather_observation
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

    return [WeatherPoint(**row) for row in rows]


@router.get("/latest", response_model=list[LatestWeather])
def get_latest_weather():
    """Most recent weather observation per zone."""
    query = """
        SELECT DISTINCT ON (zone) zone, station_id, timestamp_utc, temperature_c, wind_speed_ms, precipitation_mm
        FROM weather_observation
        ORDER BY zone, timestamp_utc DESC
    """
    with get_cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return [LatestWeather(**row) for row in rows]
