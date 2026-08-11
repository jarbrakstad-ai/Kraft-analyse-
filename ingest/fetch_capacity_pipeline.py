#!/usr/bin/env python3
"""
Fetch hydro and wind power plants that are under construction or have a
granted concession (not yet in operation) from NVE's power plant
databases, and store them in TimescaleDB (if DATABASE_URL is set) and/or
a local CSV file under ingest/output/.

This answers "how much expected effect increase is actually in the
pipeline per price area" — a fact feed for the kraftutbygging discussion,
not a forecast. Field-name mapping was confirmed against a live API
response 2026-08 (see nve/client.py for the exact fields and boolean-flag
logic used for hydro). Wind will always come back empty: NVE's public API
only exposes an "in operation" wind endpoint, confirmed (both by the
response shape and by checking NVE's own API docs directly) to have no
under-construction/concession-granted data available at all — a confirmed
gap in NVE's public API, not something this script is missing.

No API key needed — NVE's endpoints are public.

Usage:
    python fetch_capacity_pipeline.py
    python fetch_capacity_pipeline.py --sources hydro
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nve.client import NveApiError, NveClient, PlantPipelineEntry
from nve.zones import zone_from_county

OUTPUT_DIR = Path(__file__).parent / "output"


def _zone_for(entry: PlantPipelineEntry) -> str | None:
    """Prefer NVE's own elspot zone number (confirmed live, exact) over the county->zone approximation."""
    return entry.elspot_zone or zone_from_county(entry.county)


def write_csv(rows: list[tuple[str, PlantPipelineEntry, str | None]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["source_type", "plant_id", "name", "status", "municipality", "county", "zone",
             "installed_effect_mw", "expected_commissioning"]
        )
        for source_type, e, zone in sorted(rows, key=lambda r: (r[0], r[1].name)):
            writer.writerow(
                [source_type, e.plant_id, e.name, e.status, e.municipality, e.county, zone,
                 e.installed_effect_mw, e.expected_commissioning.isoformat() if e.expected_commissioning else None]
            )
    print(f"Wrote {len(rows)} rows to {path}")


def write_db(rows: list[tuple[str, PlantPipelineEntry, str | None]], database_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO capacity_pipeline
                    (source_type, plant_id, name, status, municipality, county, zone,
                     installed_effect_mw, expected_commissioning, source)
                VALUES %s
                ON CONFLICT (source_type, plant_id, source) DO UPDATE
                    SET name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        municipality = EXCLUDED.municipality,
                        county = EXCLUDED.county,
                        zone = EXCLUDED.zone,
                        installed_effect_mw = EXCLUDED.installed_effect_mw,
                        expected_commissioning = EXCLUDED.expected_commissioning
                """,
                [
                    (source_type, e.plant_id, e.name, e.status, e.municipality, e.county, zone,
                     e.installed_effect_mw, e.expected_commissioning, "nve")
                    for source_type, e, zone in rows
                ],
            )
        print(f"Upserted {len(rows)} rows into capacity_pipeline")
    finally:
        conn.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=["hydro", "wind"], default=["hydro", "wind"])
    parser.add_argument("--csv", default=str(OUTPUT_DIR / "capacity_pipeline.csv"), help="Path to write CSV output")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to the database even if DATABASE_URL is set")
    args = parser.parse_args()

    client = NveClient()
    rows: list[tuple[str, PlantPipelineEntry, str | None]] = []

    if "hydro" in args.sources:
        print("Fetching hydro power plant pipeline from NVE...")
        try:
            entries = client.get_hydro_capacity_pipeline()
            print(f"  {len(entries)} hydro plants under construction / with granted concession")
            rows += [("hydro", e, _zone_for(e)) for e in entries]
        except NveApiError as exc:
            print(f"  FAILED — {exc}", file=sys.stderr)

    if "wind" in args.sources:
        print("Fetching wind power plant pipeline from NVE...")
        try:
            entries = client.get_wind_capacity_pipeline()
            print(f"  {len(entries)} wind plants under construction / with granted concession")
            if not entries:
                print("  (0 is expected — NVE's API has no wind pipeline data available, see nve/client.py)")
            rows += [("wind", e, _zone_for(e)) for e in entries]
        except NveApiError as exc:
            print(f"  FAILED — {exc}", file=sys.stderr)

    if not rows:
        print("No pipeline entries fetched — nothing to write.", file=sys.stderr)
        return 1

    unmapped = sum(1 for _, _, zone in rows if zone is None)
    if unmapped:
        print(f"Note: {unmapped} of {len(rows)} entries had no county->zone mapping (kept, with zone=NULL).")

    write_csv(rows, Path(args.csv))

    database_url = os.environ.get("DATABASE_URL")
    if database_url and not args.no_db:
        write_db(rows, database_url)
    else:
        print("DATABASE_URL not set (or --no-db passed) — skipped database write.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
