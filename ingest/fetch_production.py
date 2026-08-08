#!/usr/bin/env python3
"""
Fetch actual generation per production type (hydro, wind, solar, thermal,
...) for NO1-NO5 and selected European zones from ENTSO-E, and store the
results in TimescaleDB (if DATABASE_URL is set) and/or a local CSV file
under ingest/output/.

Usage:
    python fetch_production.py                # last 7 days, all default zones
    python fetch_production.py --days 14
    python fetch_production.py --zones NO1 NO2 DE_LU
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

from entsoe.client import EntsoeApiError, EntsoeClient, ProductionPoint
from entsoe.zones import DEFAULT_ZONES, ZONES

OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_all(client: EntsoeClient, zones: list[str], period_start: datetime, period_end: datetime) -> list[ProductionPoint]:
    all_points: list[ProductionPoint] = []
    for zone in zones:
        eic = ZONES[zone]
        try:
            points = client.get_actual_generation_per_type(zone, eic, period_start, period_end)
            print(f"  {zone}: {len(points)} production points")
            all_points.extend(points)
        except EntsoeApiError as exc:
            print(f"  {zone}: FAILED — {exc}", file=sys.stderr)
        # Be polite to the API between zone requests.
        time.sleep(1)
    return all_points


def write_csv(points: list[ProductionPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["zone", "timestamp_utc", "production_type", "quantity_mw", "resolution_min"])
        for p in sorted(points, key=lambda p: (p.zone, p.production_type, p.timestamp_utc)):
            writer.writerow([p.zone, p.timestamp_utc.isoformat(), p.production_type, p.quantity_mw, p.resolution_min])
    print(f"Wrote {len(points)} rows to {path}")


def write_db(points: list[ProductionPoint], database_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO production_per_source (zone, timestamp_utc, production_type, quantity_mw, source)
                VALUES %s
                ON CONFLICT (zone, timestamp_utc, production_type, source) DO UPDATE
                    SET quantity_mw = EXCLUDED.quantity_mw
                """,
                [(p.zone, p.timestamp_utc, p.production_type, p.quantity_mw, "entsoe") for p in points],
            )
        print(f"Upserted {len(points)} rows into production_per_source")
    finally:
        conn.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Number of trailing days to fetch (default: 7)")
    parser.add_argument("--zones", nargs="+", choices=list(ZONES.keys()), default=DEFAULT_ZONES)
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "production.csv"), help="Path to write CSV output")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to the database even if DATABASE_URL is set")
    args = parser.parse_args()

    api_key = os.environ.get("ENTSOE_API_KEY")
    if not api_key:
        print("ERROR: ENTSOE_API_KEY is not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    period_end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    period_start = period_end - timedelta(days=args.days)

    print(f"Fetching actual generation per type for {args.zones} from {period_start} to {period_end}")
    client = EntsoeClient(api_key=api_key)
    points = fetch_all(client, args.zones, period_start, period_end)

    if not points:
        print("No production points fetched — nothing to write.", file=sys.stderr)
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
