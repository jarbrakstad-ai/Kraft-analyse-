#!/usr/bin/env python3
"""
Orchestrator for the periodic ingest run — meant to be invoked from cron.

Runs every fetch_*.py script's main() in turn, catching and logging failures
per-source so a missing API key or a single upstream outage doesn't block the
others (e.g. NVE reservoir data has no key and should keep updating even if
ENTSOE_API_KEY is unset). Exits non-zero only if every source failed.

Usage: python ingest/run_all.py [--days N]
"""

import argparse
import sys
import traceback
from datetime import datetime, timezone

import fetch_consumption
import fetch_flow
import fetch_prices
import fetch_production
import fetch_reservoir
import fetch_weather

# (label, module, extra argv for that module's own argparse)
JOBS = [
    ("priser", fetch_prices, []),
    ("produksjon", fetch_production, []),
    ("flyt", fetch_flow, []),
    ("forbruk", fetch_consumption, []),
    ("vaer", fetch_weather, []),
    ("magasin", fetch_reservoir, ["--days", "365"]),  # weekly series, keep full history
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="Trailing days to (re)fetch for the hourly sources (default: 2, overlaps the previous run so a "
        "missed hour self-heals; DB writes are upserts so this is safe to re-run).",
    )
    args = parser.parse_args()

    print(f"=== Ingest run started {datetime.now(timezone.utc).isoformat()} ===")

    results: dict[str, bool] = {}
    for label, module, extra_argv in JOBS:
        argv = extra_argv if extra_argv else ["--days", str(args.days)]
        print(f"\n--- {label} ({module.__name__} {' '.join(argv)}) ---")
        try:
            results[label] = _run_with_argv(module.main, argv) == 0
        except Exception:
            print(f"UNHANDLED EXCEPTION in {label}:", file=sys.stderr)
            traceback.print_exc()
            results[label] = False

    print("\n=== Summary ===")
    for label, ok in results.items():
        print(f"{label}: {'OK' if ok else 'FEILET'}")

    if not any(results.values()):
        print("Alle kilder feilet.", file=sys.stderr)
        return 1
    return 0


def _run_with_argv(fn, argv: list[str]) -> int:
    old_argv = sys.argv
    sys.argv = [old_argv[0], *argv]
    try:
        return fn()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
