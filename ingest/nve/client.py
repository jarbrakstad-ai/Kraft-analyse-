"""
NVE Magasinstatistikk API client — Norway's official weekly reservoir fill
level data. Public API, no key required.

Endpoint: https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData
Docs / background: https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/

IMPORTANT: this integration has NOT been verified against a live response —
outbound network access to nve.no was blocked in the environment this was
built in. Field names below are based on NVE's documented schema, but if
the API has changed, `_parse_rows` will raise a clear NveApiError showing
the actual keys it found rather than silently mis-mapping data. Run
`python fetch_reservoir.py --days 14` and check the error message (if any)
before relying on this in production.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

BASE_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

# NVE's documented field names as of the last time this schema was checked
# against public references. omrType "EL" = elspot bidding zone (paired
# with numeric omrnr 1-5), "NO" = national aggregate.
FIELD_YEAR = "iso_aar"
FIELD_WEEK = "iso_uke"
FIELD_AREA_TYPE = "omrType"
FIELD_AREA_NR = "omrnr"
FIELD_FILL_FRACTION = "fyllingsgrad"
FIELD_CAPACITY_TWH = "kapasitet_TWh"


class NveApiError(RuntimeError):
    pass


@dataclass
class ReservoirPoint:
    zone: str
    week_start_utc: datetime
    fill_percent: float
    capacity_gwh: float | None


def _iso_week_monday_utc(year: int, week: int) -> datetime:
    d = date.fromisocalendar(year, week, 1)  # ISO weekday 1 = Monday
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


class NveClient:
    def __init__(self, session: requests.Session | None = None, max_retries: int = 3):
        self.session = session or requests.Session()
        self.max_retries = max_retries

    def _get(self) -> list[dict]:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(BASE_URL, timeout=60)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 * attempt)
                continue

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                time.sleep(5 * attempt)
                continue

            raise NveApiError(f"NVE API error {resp.status_code}: {resp.text[:500]}")

        raise NveApiError(f"NVE request failed after {self.max_retries} attempts: {last_exc}")

    def get_reservoir_fill(self) -> list[ReservoirPoint]:
        """
        Fetch the full history of weekly reservoir fill levels for all
        Norwegian elspot zones (NO1-NO5) and the national aggregate ("NO").
        The API does not support server-side date filtering — filter the
        result client-side (see fetch_reservoir.py).
        """
        rows = self._get()
        return self._parse_rows(rows)

    @staticmethod
    def _zone_from_row(row: dict) -> str:
        area_type = row.get(FIELD_AREA_TYPE)
        if area_type == "EL":
            return f"NO{row[FIELD_AREA_NR]}"
        if area_type == "NO":
            return "NO"
        raise NveApiError(f"Unknown '{FIELD_AREA_TYPE}' value '{area_type}' in NVE row: {row}")

    @classmethod
    def _parse_rows(cls, rows: list[dict]) -> list[ReservoirPoint]:
        if not rows:
            return []

        required = {FIELD_YEAR, FIELD_WEEK, FIELD_AREA_TYPE, FIELD_FILL_FRACTION}
        missing = required - set(rows[0].keys())
        if missing:
            raise NveApiError(
                f"NVE response schema doesn't match expected fields. "
                f"Missing: {sorted(missing)}. Actual keys in first row: {sorted(rows[0].keys())}. "
                f"Update the FIELD_* constants in nve/client.py to match."
            )

        points: list[ReservoirPoint] = []
        for row in rows:
            try:
                zone = cls._zone_from_row(row)
                week_start = _iso_week_monday_utc(int(row[FIELD_YEAR]), int(row[FIELD_WEEK]))
                fill_fraction = row[FIELD_FILL_FRACTION]
                if fill_fraction is None:
                    continue
                capacity_twh = row.get(FIELD_CAPACITY_TWH)
            except (KeyError, ValueError, TypeError) as exc:
                raise NveApiError(f"Failed to parse NVE row {row}: {exc}") from exc

            points.append(
                ReservoirPoint(
                    zone=zone,
                    week_start_utc=week_start,
                    fill_percent=float(fill_fraction) * 100.0,
                    capacity_gwh=float(capacity_twh) * 1000.0 if capacity_twh is not None else None,
                )
            )

        return points
