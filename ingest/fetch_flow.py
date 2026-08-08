#!/usr/bin/env python3
"""
Fetch cross-border physical flow for a selection of Norwegian
interconnectors (NorNed, NordLink, North Sea Link, Skagerrak, Kontiskan)
from ENTSO-E, and store the results in TimescaleDB (if DATABASE_URL is
set) and/or a local CSV file under ingest/output/.

Each interconnector is fetched in both directions, since flow can go
either way depending on the hour — the direction that carried no power in
a given hour simply won't have a row.

Usage:
    python fetch_flow.py                        # last 7 days, all interconnectors
    python fetch_flow.py --days 14
    python fetch_flow.py --interconnectors NorNed Skagerrak
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

from entsoe.client import EntsoeApiError, EntsoeClient, FlowPoint
from entsoe.interconnectors import INTERCONNECTOR_ZONE_EIC, INTERCONNECTORS

OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_all(client: EntsoeClient, interconnectors: list[str], period_start: datetime, period_end: datetime) -> list[tuple[str, FlowPoint]]:
    """Returns (interconnector_name, FlowPoint) pairs for both directions of each interconnector."""
    results: list[tuple[str, FlowPoint]] = []
    for name in interconnectors:
        zone_a, zone_b = INTERCONNECTORS[name]
        eic_a = INTERCONNECTOR_ZONE_EIC[zone_a]
        eic_b = INTERCONNECTOR_ZONE_EIC[zone_b]

        for from_zone, from_eic, to_zone, to_eic in [(zone_a, eic_a, zone_b, eic_b), (zone_b, eic_b, zone_a, eic_a)]:
            try:
                points = client.get_cross_border_flow(from_zone, from_eic, to_zone, to_eic, period_start, period_end)
                print(f"  {name} {from_zone}->{to_zone}: {len(points)} flow points")
                results.extend((name, p) for p in points)
            except EntsoeApiError as exc:
                print(f"  {name} {from_zone}->{to_zone}: FAILED — {exc}", file=sys.stderr)
            time.sleep(1)

    return results


def write_csv(results: list[tuple[str, FlowPoint]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["interconnector", "from_zone", "to_zone", "timestamp_utc", "flow_mw", "resolution_min"])
        for name, p in sorted(results, key=lambda r: (r[0], r[1].from_zone, r[1].timestamp_utc)):
            writer.writerow([name, p.from_zone, p.to_zone, p.timestamp_utc.isoformat(), p.flow_mw, p.resolution_min])
    print(f"Wrote {len(results)} rows to {path}")


def write_db(results: list[tuple[str, FlowPoint]], database_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO cross_border_flow (from_zone, to_zone, interconnector, timestamp_utc, flow_mw, source)
                VALUES %s
                ON CONFLICT (from_zone, to_zone, timestamp_utc, source) DO UPDATE
                    SET flow_mw = EXCLUDED.flow_mw,
                        interconnector = EXCLUDED.interconnector
                """,
                [(p.from_zone, p.to_zone, name, p.timestamp_utc, p.flow_mw, "entsoe") for name, p in results],
            )
        print(f"Upserted {len(results)} rows into cross_border_flow")
    finally:
        conn.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Number of trailing days to fetch (default: 7)")
    parser.add_argument("--interconnectors", nargs="+", choices=list(INTERCONNECTORS.keys()), default=list(INTERCONNECTORS.keys()))
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "flow.csv"), help="Path to write CSV output")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to the database even if DATABASE_URL is set")
    args = parser.parse_args()

    api_key = os.environ.get("ENTSOE_API_KEY")
    if not api_key:
        print("ERROR: ENTSOE_API_KEY is not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    period_end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    period_start = period_end - timedelta(days=args.days)

    print(f"Fetching cross-border flow for {args.interconnectors} from {period_start} to {period_end}")
    client = EntsoeClient(api_key=api_key)
    results = fetch_all(client, args.interconnectors, period_start, period_end)

    if not results:
        print("No flow points fetched — nothing to write.", file=sys.stderr)
        return 1

    write_csv(results, Path(args.csv))

    database_url = os.environ.get("DATABASE_URL")
    if database_url and not args.no_db:
        write_db(results, database_url)
    else:
        print("DATABASE_URL not set (or --no-db passed) — skipped database write.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
