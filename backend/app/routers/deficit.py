from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_cursor
from ..ml.predict import ModelNotTrainedError, NoRecentDataError, get_deficit_model_info, predict_next_day_deficit_for_zone
from ..schemas import BalancePoint, DeficitForecast, DeficitForecastZone, DeficitSummary, ModelInfo
from ..zones import AGGREGATE_ZONE_GROUPS, validate_zone_or_aggregate

router = APIRouter(prefix="/deficit", tags=["deficit"])


def _zones_for(zone: str) -> list[str]:
    return AGGREGATE_ZONE_GROUPS.get(zone, [zone])


@router.get("", response_model=DeficitSummary)
def get_deficit(
    zone: str = Query(..., description="Zone code (e.g. NO1), or an aggregate: 'NO' (NO1-NO5) or 'EU' (tracked European zones)."),
    start: datetime | None = Query(None, description="Start of range (UTC, ISO 8601). Defaults to 7 days ago."),
    end: datetime | None = Query(None, description="End of range (UTC, ISO 8601). Defaults to now."),
    limit: int = Query(2000, ge=1, le=10000),
):
    """
    Actual historical supply/demand balance (production minus consumption,
    MW), hourly. Negative balance_mw means the zone drew more than it
    produced that hour (a deficit, covered by imports). For 'NO' or 'EU',
    production and consumption are each summed across the group's zones
    before taking the difference.
    """
    validate_zone_or_aggregate(zone)
    zones = _zones_for(zone)

    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="'start' must be before 'end'")

    query = """
        WITH prod AS (
            SELECT timestamp_utc, sum(quantity_mw) AS production_mw
            FROM production_per_source
            WHERE zone = ANY(%(zones)s) AND timestamp_utc >= %(start)s AND timestamp_utc < %(end)s
            GROUP BY timestamp_utc
        ),
        cons AS (
            SELECT timestamp_utc, sum(load_mw) AS load_mw
            FROM consumption
            WHERE zone = ANY(%(zones)s) AND timestamp_utc >= %(start)s AND timestamp_utc < %(end)s
            GROUP BY timestamp_utc
        )
        SELECT prod.timestamp_utc, prod.production_mw, cons.load_mw, (prod.production_mw - cons.load_mw) AS balance_mw
        FROM prod
        JOIN cons ON cons.timestamp_utc = prod.timestamp_utc
        ORDER BY prod.timestamp_utc
        LIMIT %(limit)s
    """
    params = {"zones": zones, "start": start, "end": end, "limit": limit}

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    points = [BalancePoint(**row) for row in rows]
    n = len(points)
    avg_balance = sum(p.balance_mw for p in points) / n if n else 0.0
    hours_in_deficit = sum(1 for p in points if p.balance_mw < 0)

    return DeficitSummary(zone=zone, n=n, avg_balance_mw=avg_balance, hours_in_deficit=hours_in_deficit, points=points)


@router.get("/forecast", response_model=DeficitForecast)
def get_deficit_forecast(
    zone: str = Query(..., description="Zone code (e.g. NO1), or an aggregate: 'NO' (NO1-NO5) or 'EU' (tracked European zones)."),
):
    """
    Predicted next-day supply/demand balance. For a real zone, this is a
    direct model prediction. For 'NO'/'EU', each constituent zone is
    predicted separately and summed — the model is trained per-zone, not
    on pre-aggregated data, so aggregates are always a sum of individual
    forecasts, shown in zone_breakdown for transparency.
    """
    validate_zone_or_aggregate(zone)
    zones = _zones_for(zone)
    is_aggregate = zone in AGGREGATE_ZONE_GROUPS

    breakdown: list[DeficitForecastZone] = []
    based_on_day = None
    model_trained_at = None
    errors: list[str] = []

    try:
        for z in zones:
            try:
                result = predict_next_day_deficit_for_zone(z)
            except NoRecentDataError as exc:
                errors.append(str(exc))
                continue

            based_on_day = result["based_on_day"]
            model_trained_at = result["model_trained_at"]
            breakdown.append(
                DeficitForecastZone(
                    zone=z,
                    predicted_balance_mw=result["predicted_balance_mw"],
                    based_on_production_mw=result["based_on_production_mw"],
                    based_on_load_mw=result["based_on_load_mw"],
                    missing_features=result["missing_features"],
                )
            )
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not breakdown:
        raise HTTPException(status_code=404, detail="; ".join(errors) or f"No forecast available for zone '{zone}'.")

    total_balance = sum(b.predicted_balance_mw for b in breakdown)

    return DeficitForecast(
        zone=zone,
        based_on_day=based_on_day,
        predicted_date=based_on_day + timedelta(days=1),
        predicted_balance_mw=total_balance,
        is_aggregate=is_aggregate,
        zone_breakdown=breakdown,
        model_trained_at=model_trained_at,
    )


@router.get("/model-info", response_model=ModelInfo)
def deficit_model_info():
    """Metadata about the currently loaded deficit model: when it was trained, holdout metrics, feature importances."""
    try:
        return ModelInfo(**get_deficit_model_info())
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
