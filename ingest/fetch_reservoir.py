#!/usr/bin/env python3
"""
Fetch weekly reservoir (magasin) fill levels for NO1-NO5 and the national
aggregate from NVE's Magasinstatistikk API, and store the results in
TimescaleDB (if DATABASE_URL is set) and/or a local CSV file under
ingest/output/.

Unlike the ENTSO-E-backed scripts, this needs no API key — NVE's endpoint
is public. It also returns the full history in one response (no date
range parameters), so filtering to the trailing N days happens locally.

Usage:
    python fetch_reservoir.py                # last 365 days, all zones
    python fetch_reservoir.py --days 90
    python fetch_reservoir.py --zones NO1 NO2 NO
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from nve.client import NveApiError, NveClient, ReservoirPoint

OUTPUT_DIR = Path(__file__).parent / "output"
ALL_ZONES = ["NO1", "NO2", "NO3", "NO4", "NO5", "NO"]


def write_csv(points: list[ReservoirPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["zone", "week_start_utc", "fill_percent", "capacity_gwh"])
        for p in sorted(points, key=lambda p: (p.zone, p.week_start_utc)):
            writer.writerow([p.zone, p.week_start_utc.isoformat(), p.fill_percent, p.capacity_gwh])
    print(f"Wrote {len(points)} rows to {path}")


def write_db(points: list[ReservoirPoint], database_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO reservoir_fill (zone, week_start_utc, fill_percent, capacity_gwh, source)
                VALUES %s
                ON CONFLICT (zone, week_start_utc, source) DO UPDATE
                    SET fill_percent = EXCLUDED.fill_percent,
                        capacity_gwh = EXCLUDED.capacity_gwh
                """,
                [(p.zone, p.week_start_utc, p.fill_percent, p.capacity_gwh, "nve") for p in points],
            )
        print(f"Upserted {len(points)} rows into reservoir_fill")
    finally:
        conn.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365, help="Number of trailing days to keep (default: 365)")
    parser.add_argument("--zones", nargs="+", choices=ALL_ZONES, default=ALL_ZONES)
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "reservoir.csv"), help="Path to write CSV output")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to the database even if DATABASE_URL is set")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    print("Fetching full reservoir fill history from NVE...")
    client = NveClient()
    try:
        all_points = client.get_reservoir_fill()
    except NveApiError as exc:
        print(f"FAILED — {exc}", file=sys.stderr)
        return 1

    points = [p for p in all_points if p.zone in args.zones and p.week_start_utc >= cutoff]
    print(f"Kept {len(points)} of {len(all_points)} points after filtering to zones={args.zones}, days={args.days}")

    if not points:
        print("No reservoir points after filtering — nothing to write.", file=sys.stderr)
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
