"""
MET Norway Frost API client — historical weather observations.

Docs: https://frost.met.no/api.html
Requires a free client ID, obtained by registering at
https://frost.met.no/auth/requestCredentials.html (no approval wait, key
issued immediately).

IMPORTANT: this integration has NOT been verified against a live response
— outbound network access to frost.met.no was blocked in the environment
this was built in. The response structure (data[].referenceTime,
data[].observations[].elementId/value) is based on Frost API v0's
documented schema, and `_parse_observations` validates the top-level shape
and raises a clear FrostApiError if it doesn't match, rather than silently
mis-mapping data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

BASE_URL = "https://frost.met.no/observations/v0.jsonld"

# Frost element IDs we request. sum(precipitation_amount PT1H) uses hourly
# accumulation; MET's naming convention embeds the aggregation in the ID.
ELEMENTS = ["air_temperature", "wind_speed", "sum(precipitation_amount PT1H)"]


class FrostApiError(RuntimeError):
    pass


@dataclass
class WeatherPoint:
    zone: str
    station_id: str
    timestamp_utc: datetime
    temperature_c: float | None
    wind_speed_ms: float | None
    precipitation_mm: float | None


class FrostClient:
    def __init__(self, client_id: str, session: requests.Session | None = None, max_retries: int = 3):
        if not client_id:
            raise ValueError("MET Frost client ID is required")
        self.client_id = client_id
        self.session = session or requests.Session()
        self.max_retries = max_retries

    def _get(self, params: dict) -> dict | None:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(BASE_URL, params=params, auth=(self.client_id, ""), timeout=30)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 * attempt)
                continue

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 412:
                # "Precondition failed" — no data for this station/element/
                # time window combination. Not an error, just empty.
                return None

            if resp.status_code == 429:
                time.sleep(5 * attempt)
                continue

            raise FrostApiError(f"Frost API error {resp.status_code} for params={params}: {resp.text[:500]}")

        raise FrostApiError(f"Frost request failed after {self.max_retries} attempts: {last_exc}")

    def get_weather(self, zone: str, station_id: str, period_start: datetime, period_end: datetime) -> list[WeatherPoint]:
        """
        Fetch hourly temperature, wind speed and precipitation for one
        station over [period_start, period_end).
        """
        params = {
            "sources": station_id,
            "elements": ",".join(ELEMENTS),
            "referencetime": f"{period_start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{period_end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        }
        response_json = self._get(params)
        if response_json is None:
            return []
        return self._parse_observations(response_json, zone, station_id)

    @staticmethod
    def _parse_observations(response_json: dict, zone: str, station_id: str) -> list[WeatherPoint]:
        if "data" not in response_json:
            raise FrostApiError(
                f"Frost response schema doesn't match expected shape — no 'data' key. "
                f"Top-level keys found: {sorted(response_json.keys())}."
            )

        # Group by referenceTime since different elements (instantaneous vs.
        # hourly-accumulated) can arrive as separate entries for the same
        # station and timestamp.
        by_timestamp: dict[datetime, dict[str, float]] = {}
        for item in response_json["data"]:
            try:
                ts = datetime.strptime(item["referenceTime"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError) as exc:
                raise FrostApiError(f"Failed to parse referenceTime from Frost data item: {item}") from exc

            bucket = by_timestamp.setdefault(ts, {})
            for obs in item.get("observations", []):
                element_id = obs.get("elementId")
                value = obs.get("value")
                if element_id is not None and value is not None:
                    bucket[element_id] = value

        points = [
            WeatherPoint(
                zone=zone,
                station_id=station_id,
                timestamp_utc=ts,
                temperature_c=values.get("air_temperature"),
                wind_speed_ms=values.get("wind_speed"),
                precipitation_mm=values.get("sum(precipitation_amount PT1H)"),
            )
            for ts, values in sorted(by_timestamp.items())
        ]
        return points
