#!/usr/bin/env python3
"""
Fetch hourly weather observations (temperature, wind speed, precipitation)
for one representative station per Norwegian bidding zone from MET
Norway's Frost API, and store the results in TimescaleDB (if DATABASE_URL
is set) and/or a local CSV file under ingest/output/.

Weather is a useful explanatory variable for the price/production
analysis: temperature drives heating demand, wind speed drives wind
production, and precipitation drives hydro inflow and reservoir fill.

Usage:
    python fetch_weather.py                # last 7 days, all zones
    python fetch_weather.py --days 14
    python fetch_weather.py --zones NO1 NO3
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from met.client import FrostApiError, FrostClient, WeatherPoint
from met.stations import DEFAULT_ZONES, STATIONS

OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_all(client: FrostClient, zones: list[str], period_start: datetime, period_end: datetime) -> list[WeatherPoint]:
    all_points: list[WeatherPoint] = []
    for zone in zones:
        station_id = STATIONS[zone]
        try:
            points = client.get_weather(zone, station_id, period_start, period_end)
            print(f"  {zone} ({station_id}): {len(points)} weather points")
            all_points.extend(points)
        except FrostApiError as exc:
            print(f"  {zone} ({station_id}): FAILED — {exc}", file=sys.stderr)
        time.sleep(1)
    return all_points


def write_csv(points: list[WeatherPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["zone", "station_id", "timestamp_utc", "temperature_c", "wind_speed_ms", "precipitation_mm"])
        for p in sorted(points, key=lambda p: (p.zone, p.timestamp_utc)):
            writer.writerow([p.zone, p.station_id, p.timestamp_utc.isoformat(), p.temperature_c, p.wind_speed_ms, p.precipitation_mm])
    print(f"Wrote {len(points)} rows to {path}")


def write_db(points: list[WeatherPoint], database_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO weather_observation
                    (zone, station_id, timestamp_utc, temperature_c, wind_speed_ms, precipitation_mm, source)
                VALUES %s
                ON CONFLICT (zone, timestamp_utc, source) DO UPDATE
                    SET temperature_c = EXCLUDED.temperature_c,
                        wind_speed_ms = EXCLUDED.wind_speed_ms,
                        precipitation_mm = EXCLUDED.precipitation_mm,
                        station_id = EXCLUDED.station_id
                """,
                [
                    (p.zone, p.station_id, p.timestamp_utc, p.temperature_c, p.wind_speed_ms, p.precipitation_mm, "met_frost")
                    for p in points
                ],
            )
        print(f"Upserted {len(points)} rows into weather_observation")
    finally:
        conn.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Number of trailing days to fetch (default: 7)")
    parser.add_argument("--zones", nargs="+", choices=list(STATIONS.keys()), default=DEFAULT_ZONES)
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "weather.csv"), help="Path to write CSV output")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to the database even if DATABASE_URL is set")
    args = parser.parse_args()

    client_id = os.environ.get("MET_FROST_CLIENT_ID")
    if not client_id:
        print("ERROR: MET_FROST_CLIENT_ID is not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    period_end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    period_start = period_end - timedelta(days=args.days)

    print(f"Fetching weather for {args.zones} from {period_start} to {period_end}")
    client = FrostClient(client_id=client_id)
    points = fetch_all(client, args.zones, period_start, period_end)

    if not points:
        print("No weather points fetched — nothing to write.", file=sys.stderr)
        return 1

    write_csv(points, Path(args.csv))

    database_url = os.environ.get("DATABASE_URL")
    if database_url and not args.no_db:
        write_db(points, database_url)
    else:
        print("DATABASE_URL not set (or --no-db passed) — skipped database write.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
