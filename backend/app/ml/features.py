"""
Feature engineering for the next-day price prediction model.

Builds one row per (zone, day) from all five data sources (price,
production, flow, reservoir, weather), with lag features and a next-day
price target. Used identically by train.py (historical training frame)
and predict.py (today's feature row, for tomorrow's prediction) so the
model always sees the same feature shape it was trained on.

Missing sources for a given zone (e.g. no reservoir/weather data for
European zones) are left as NaN rather than imputed — HistGradientBoosting
handles missing values natively, and NaN is more honest than a fabricated
zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..db import get_conn

# Broad production-type buckets, mapped from the granular types written by
# ingest/entsoe/production_types.py. Shares are relative (sum to ~1 per
# zone/day), which generalizes across zones with very different absolute
# production scales better than raw MW columns would.
PRODUCTION_BUCKETS = {
    "hydro": "hydro_share",
    "hydro_pumped_storage": "hydro_share",
    "wind_onshore": "wind_share",
    "wind_offshore": "wind_share",
    "solar": "solar_share",
}
DEFAULT_BUCKET = "thermal_other_share"
SHARE_COLUMNS = ["hydro_share", "wind_share", "solar_share", "thermal_other_share"]

FEATURE_COLUMNS = [
    "zone",
    "price_avg",
    "price_min",
    "price_max",
    "price_avg_lag1",
    "price_avg_lag2",
    "hydro_share",
    "wind_share",
    "solar_share",
    "thermal_other_share",
    "total_production_mw",
    "fill_percent",
    "temp_avg",
    "wind_avg",
    "precip_sum",
    "net_flow_mw",
    "day_of_week",
    "month",
]
TARGET_COLUMN = "target_next_day_avg_price"


def _daily_price(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT zone, date_trunc('day', timestamp_utc)::date AS day,
               avg(price_eur_mwh) AS price_avg,
               min(price_eur_mwh) AS price_min,
               max(price_eur_mwh) AS price_max
        FROM spot_price
        GROUP BY zone, day
        """,
        conn,
    )


def _daily_production_shares(conn) -> pd.DataFrame:
    raw = pd.read_sql(
        """
        SELECT zone, date_trunc('day', timestamp_utc)::date AS day, production_type, avg(quantity_mw) AS avg_mw
        FROM production_per_source
        GROUP BY zone, day, production_type
        """,
        conn,
    )
    if raw.empty:
        return pd.DataFrame(columns=["zone", "day", "total_production_mw", *SHARE_COLUMNS])

    raw["bucket"] = raw["production_type"].map(PRODUCTION_BUCKETS).fillna(DEFAULT_BUCKET)
    totals = raw.groupby(["zone", "day"])["avg_mw"].sum().rename("total_production_mw")
    by_bucket = raw.groupby(["zone", "day", "bucket"])["avg_mw"].sum().unstack("bucket").reindex(columns=SHARE_COLUMNS)

    merged = by_bucket.join(totals).reset_index()
    for col in SHARE_COLUMNS:
        merged[col] = merged[col].fillna(0.0) / merged["total_production_mw"].replace(0, np.nan)
    return merged


def _daily_weather(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT zone, date_trunc('day', timestamp_utc)::date AS day,
               avg(temperature_c) AS temp_avg,
               avg(wind_speed_ms) AS wind_avg,
               sum(precipitation_mm) AS precip_sum
        FROM weather_observation
        GROUP BY zone, day
        """,
        conn,
    )


def _daily_net_flow(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT zone, day, sum(net_mw) AS net_flow_mw
        FROM (
            SELECT from_zone AS zone, date_trunc('day', timestamp_utc)::date AS day, flow_mw AS net_mw
            FROM cross_border_flow
            UNION ALL
            SELECT to_zone AS zone, date_trunc('day', timestamp_utc)::date AS day, -flow_mw AS net_mw
            FROM cross_border_flow
        ) t
        GROUP BY zone, day
        """,
        conn,
    )


def _weekly_reservoir(conn) -> pd.DataFrame:
    df = pd.read_sql("SELECT zone, week_start_utc::date AS week_start, fill_percent FROM reservoir_fill", conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df.sort_values("week_start")


def _attach_reservoir(daily: pd.DataFrame, reservoir: pd.DataFrame) -> pd.DataFrame:
    """As-of join: each day gets the most recent fill_percent at or before that day, per zone."""
    if reservoir.empty:
        daily["fill_percent"] = np.nan
        return daily

    parts = []
    for zone, group in daily.groupby("zone"):
        res_zone = reservoir[reservoir["zone"] == zone]
        if res_zone.empty:
            group = group.copy()
            group["fill_percent"] = np.nan
            parts.append(group)
            continue
        merged = pd.merge_asof(
            group.sort_values("day"),
            res_zone.sort_values("week_start")[["week_start", "fill_percent"]],
            left_on="day",
            right_on="week_start",
            direction="backward",
        ).drop(columns="week_start")
        parts.append(merged)
    return pd.concat(parts, ignore_index=True)


def _base_daily_table(conn) -> pd.DataFrame:
    """One row per (zone, day) with all engineered features, no target column."""
    price = _daily_price(conn)
    if price.empty:
        return pd.DataFrame(columns=["zone", "day", *FEATURE_COLUMNS])

    production = _daily_production_shares(conn)
    weather = _daily_weather(conn)
    flow = _daily_net_flow(conn)
    reservoir = _weekly_reservoir(conn)

    daily = price.merge(production, on=["zone", "day"], how="left")
    daily = daily.merge(weather, on=["zone", "day"], how="left")
    daily = daily.merge(flow, on=["zone", "day"], how="left")
    daily["day"] = pd.to_datetime(daily["day"])
    daily = _attach_reservoir(daily, reservoir)

    daily = daily.sort_values(["zone", "day"]).reset_index(drop=True)
    daily["price_avg_lag1"] = daily.groupby("zone")["price_avg"].shift(1)
    daily["price_avg_lag2"] = daily.groupby("zone")["price_avg"].shift(2)
    daily["day_of_week"] = pd.to_datetime(daily["day"]).dt.dayofweek
    daily["month"] = pd.to_datetime(daily["day"]).dt.month

    return daily


def build_training_frame() -> pd.DataFrame:
    """
    Historical (zone, day) rows with a next-day price target, for
    train.py. Rows without a known next-day price (each zone's most
    recent day) or without the lag-1 feature (each zone's first day) are
    dropped, since both make the row unusable for supervised training.
    """
    with get_conn() as conn:
        daily = _base_daily_table(conn)

    if daily.empty:
        return daily

    daily[TARGET_COLUMN] = daily.groupby("zone")["price_avg"].shift(-1)
    daily = daily.dropna(subset=[TARGET_COLUMN, "price_avg_lag1"])
    return daily[["day", *FEATURE_COLUMNS, TARGET_COLUMN]]


def build_prediction_frame(zone: str) -> pd.DataFrame:
    """The most recent complete day's feature row for `zone`, used to predict tomorrow's price."""
    with get_conn() as conn:
        daily = _base_daily_table(conn)

    zone_rows = daily[daily["zone"] == zone].sort_values("day")
    if zone_rows.empty:
        return zone_rows

    latest = zone_rows.tail(1).copy()
    return latest[["day", *FEATURE_COLUMNS]]
