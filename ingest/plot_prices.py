#!/usr/bin/env python3
"""
Generate an interactive HTML chart of spot prices per zone over the last N
days. Reads from the database if DATABASE_URL is set, otherwise falls back
to the CSV produced by fetch_prices.py.

Usage:
    python plot_prices.py
    python plot_prices.py --days 7 --csv output/prices.csv --out output/prices_chart.html
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

OUTPUT_DIR = Path(__file__).parent / "output"


def load_from_db(database_url: str, days: int) -> pd.DataFrame:
    import psycopg2

    query = """
        SELECT zone, timestamp_utc, price_eur_mwh
        FROM spot_price
        WHERE timestamp_utc >= now() - interval '%s days'
        ORDER BY timestamp_utc
    """
    conn = psycopg2.connect(database_url)
    try:
        return pd.read_sql(query % days, conn)
    finally:
        conn.close()


def load_from_csv(csv_path: Path, days: int) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["timestamp_utc"])
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=days)
    if df["timestamp_utc"].dt.tz is None:
        df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize("UTC")
    return df[df["timestamp_utc"] >= cutoff]


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "prices.csv"))
    parser.add_argument("--out", default=str(OUTPUT_DIR / "prices_chart.html"))
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if database_url and not args.no_db:
        df = load_from_db(database_url, args.days)
    else:
        df = load_from_csv(Path(args.csv), args.days)

    if df.empty:
        print("No data to plot.")
        return 1

    fig = px.line(
        df,
        x="timestamp_utc",
        y="price_eur_mwh",
        color="zone",
        title=f"Spotpriser siste {args.days} dager (EUR/MWh)",
        labels={"timestamp_utc": "Tid (UTC)", "price_eur_mwh": "Pris (EUR/MWh)", "zone": "Sone"},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="Sone")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_path)
    print(f"Wrote chart to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
