from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..interconnectors import validate_interconnector
from ..schemas import (
    PriceProductionCorrelation,
    PriceProductionPoint,
    PriceReservoirCorrelation,
    PriceReservoirPoint,
    PriceSpreadFlowCorrelation,
    PriceSpreadFlowPoint,
    PriceWeatherCorrelation,
    PriceWeatherPoint,
    ProductionWeatherCorrelation,
    ProductionWeatherPoint,
)
from ..stats import pearson_r
from ..zones import validate_zone

router = APIRouter(prefix="/analysis", tags=["analysis"])

WEATHER_VARIABLES = {"temperature_c", "wind_speed_ms", "precipitation_mm"}


def _validate_weather_variable(name: str) -> str:
    if name not in WEATHER_VARIABLES:
        raise HTTPException(status_code=404, detail=f"Unknown weather variable '{name}'. Valid values: {sorted(WEATHER_VARIABLES)}")
    return name


@router.get("/price-vs-production", response_model=PriceProductionCorrelation)
def price_vs_production(
    zone: str = Query(..., description="Zone code, e.g. NO1."),
    production_type: str = Query(..., description="Production type, e.g. 'hydro' — see GET /production/types."),
    days: int = Query(30, ge=1, le=365),
):
    """Correlation between spot price and production of a given type, same zone, hourly."""
    validate_zone(zone)

    start = datetime.now(timezone.utc) - timedelta(days=days)
    query = """
        SELECT sp.timestamp_utc, sp.price_eur_mwh, pp.quantity_mw
        FROM spot_price sp
        JOIN production_per_source pp
            ON pp.zone = sp.zone AND pp.timestamp_utc = sp.timestamp_utc AND pp.production_type = %(production_type)s
        WHERE sp.zone = %(zone)s AND sp.timestamp_utc >= %(start)s
        ORDER BY sp.timestamp_utc
    """
    with get_cursor() as cur:
        cur.execute(query, {"zone": zone, "production_type": production_type, "start": start})
        rows = cur.fetchall()

    points = [PriceProductionPoint(**row) for row in rows]
    r = pearson_r([p.price_eur_mwh for p in points], [p.quantity_mw for p in points])
    return PriceProductionCorrelation(zone=zone, production_type=production_type, n=len(points), pearson_r=r, points=points)


@router.get("/price-vs-reservoir", response_model=PriceReservoirCorrelation)
def price_vs_reservoir(
    zone: str = Query(..., description="Zone code, e.g. NO1, or 'NO' for the national aggregate."),
    weeks: int = Query(52, ge=1, le=520),
):
    """
    Correlation between weekly average spot price and reservoir fill level,
    same zone. Price is resampled from hourly to weekly average (ISO week,
    Monday start) to align with reservoir_fill's weekly granularity.
    """
    validate_zone(zone)

    start = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    query = """
        WITH weekly_price AS (
            SELECT date_trunc('week', timestamp_utc) AS week_start_utc, avg(price_eur_mwh) AS avg_price_eur_mwh
            FROM spot_price
            WHERE zone = %(zone)s AND timestamp_utc >= %(start)s
            GROUP BY week_start_utc
        )
        SELECT wp.week_start_utc, wp.avg_price_eur_mwh, rf.fill_percent
        FROM weekly_price wp
        JOIN reservoir_fill rf ON rf.zone = %(zone)s AND rf.week_start_utc = wp.week_start_utc
        ORDER BY wp.week_start_utc
    """
    with get_cursor() as cur:
        cur.execute(query, {"zone": zone, "start": start})
        rows = cur.fetchall()

    points = [PriceReservoirPoint(**row) for row in rows]
    r = pearson_r([p.avg_price_eur_mwh for p in points], [p.fill_percent for p in points])
    return PriceReservoirCorrelation(zone=zone, n=len(points), pearson_r=r, points=points)


@router.get("/price-spread-vs-flow", response_model=PriceSpreadFlowCorrelation)
def price_spread_vs_flow(
    zone_a: str = Query(..., description="First zone, e.g. NO2."),
    zone_b: str = Query(..., description="Second zone, e.g. NL."),
    interconnector: str | None = Query(None, description="Restrict flow to a specific interconnector, e.g. 'NorNed'."),
    days: int = Query(30, ge=1, le=365),
):
    """
    Correlation between the price spread (zone_a - zone_b) and the net
    physical flow from zone_a to zone_b, hourly. A positive spread
    (zone_a more expensive) is expected to correlate with flow from
    zone_b into zone_a (i.e. a negative net_flow_mw here).
    """
    validate_zone(zone_a)
    validate_zone(zone_b)
    if interconnector is not None:
        validate_interconnector(interconnector)

    start = datetime.now(timezone.utc) - timedelta(days=days)
    interconnector_filter = "AND interconnector = %(interconnector)s" if interconnector is not None else ""
    query = f"""
        WITH spread AS (
            SELECT a.timestamp_utc, (a.price_eur_mwh - b.price_eur_mwh) AS price_spread_eur_mwh
            FROM spot_price a
            JOIN spot_price b ON b.timestamp_utc = a.timestamp_utc AND b.zone = %(zone_b)s
            WHERE a.zone = %(zone_a)s AND a.timestamp_utc >= %(start)s
        ),
        flow_ab AS (
            SELECT timestamp_utc, flow_mw FROM cross_border_flow
            WHERE from_zone = %(zone_a)s AND to_zone = %(zone_b)s {interconnector_filter}
        ),
        flow_ba AS (
            SELECT timestamp_utc, flow_mw FROM cross_border_flow
            WHERE from_zone = %(zone_b)s AND to_zone = %(zone_a)s {interconnector_filter}
        )
        SELECT
            s.timestamp_utc,
            s.price_spread_eur_mwh,
            COALESCE(fab.flow_mw, 0) - COALESCE(fba.flow_mw, 0) AS net_flow_mw
        FROM spread s
        LEFT JOIN flow_ab fab ON fab.timestamp_utc = s.timestamp_utc
        LEFT JOIN flow_ba fba ON fba.timestamp_utc = s.timestamp_utc
        WHERE fab.timestamp_utc IS NOT NULL OR fba.timestamp_utc IS NOT NULL
        ORDER BY s.timestamp_utc
    """
    params = {"zone_a": zone_a, "zone_b": zone_b, "start": start}
    if interconnector is not None:
        params["interconnector"] = interconnector

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    points = [PriceSpreadFlowPoint(**row) for row in rows]
    r = pearson_r([p.price_spread_eur_mwh for p in points], [p.net_flow_mw for p in points])
    return PriceSpreadFlowCorrelation(zone_a=zone_a, zone_b=zone_b, n=len(points), pearson_r=r, points=points)


@router.get("/price-vs-weather", response_model=PriceWeatherCorrelation)
def price_vs_weather(
    zone: str = Query(..., description="Zone code, e.g. NO1."),
    weather_variable: str = Query(..., description="One of: temperature_c, wind_speed_ms, precipitation_mm."),
    days: int = Query(30, ge=1, le=365),
):
    """Correlation between spot price and a weather variable, same zone, hourly."""
    validate_zone(zone)
    _validate_weather_variable(weather_variable)

    start = datetime.now(timezone.utc) - timedelta(days=days)
    query = f"""
        SELECT sp.timestamp_utc, sp.price_eur_mwh, w.{weather_variable} AS weather_value
        FROM spot_price sp
        JOIN weather_observation w ON w.zone = sp.zone AND w.timestamp_utc = sp.timestamp_utc
        WHERE sp.zone = %(zone)s AND sp.timestamp_utc >= %(start)s AND w.{weather_variable} IS NOT NULL
        ORDER BY sp.timestamp_utc
    """
    with get_cursor() as cur:
        cur.execute(query, {"zone": zone, "start": start})
        rows = cur.fetchall()

    points = [PriceWeatherPoint(**row) for row in rows]
    r = pearson_r([p.price_eur_mwh for p in points], [p.weather_value for p in points])
    return PriceWeatherCorrelation(zone=zone, weather_variable=weather_variable, n=len(points), pearson_r=r, points=points)


@router.get("/production-vs-weather", response_model=ProductionWeatherCorrelation)
def production_vs_weather(
    zone: str = Query(..., description="Zone code, e.g. NO1."),
    production_type: str = Query(..., description="Production type, e.g. 'wind_onshore' — see GET /production/types."),
    weather_variable: str = Query(..., description="One of: temperature_c, wind_speed_ms, precipitation_mm."),
    days: int = Query(30, ge=1, le=365),
):
    """Correlation between production of a given type and a weather variable, same zone, hourly (e.g. wind_onshore vs. wind_speed_ms)."""
    validate_zone(zone)
    _validate_weather_variable(weather_variable)

    start = datetime.now(timezone.utc) - timedelta(days=days)
    query = f"""
        SELECT pp.timestamp_utc, pp.quantity_mw, w.{weather_variable} AS weather_value
        FROM production_per_source pp
        JOIN weather_observation w ON w.zone = pp.zone AND w.timestamp_utc = pp.timestamp_utc
        WHERE pp.zone = %(zone)s AND pp.production_type = %(production_type)s
            AND pp.timestamp_utc >= %(start)s AND w.{weather_variable} IS NOT NULL
        ORDER BY pp.timestamp_utc
    """
    with get_cursor() as cur:
        cur.execute(query, {"zone": zone, "production_type": production_type, "start": start})
        rows = cur.fetchall()

    points = [ProductionWeatherPoint(**row) for row in rows]
    r = pearson_r([p.quantity_mw for p in points], [p.weather_value for p in points])
    return ProductionWeatherCorrelation(
        zone=zone, production_type=production_type, weather_variable=weather_variable, n=len(points), pearson_r=r, points=points
    )
