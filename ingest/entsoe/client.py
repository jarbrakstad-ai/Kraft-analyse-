"""
Minimal ENTSO-E Transparency Platform client.

Docs: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
Requires a free API key (Web API security token), obtained by registering an
account at https://transparency.entsoe.eu/ and requesting access under
"My Account Settings" -> "Web API Security Token".
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://web-api.tp.entsoe.eu/api"

# ENTSO-E returns XML with a namespace that varies by document type; we strip
# namespaces rather than hardcode them so parsing stays robust across types.
NS_STRIP = True


class EntsoeApiError(RuntimeError):
    pass


@dataclass
class PricePoint:
    zone: str
    timestamp_utc: datetime
    price_eur_mwh: float
    resolution_min: int


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _local_iter(elem):
    """Iterate an XML element's children by local (namespace-stripped) tag name."""
    for child in elem:
        yield _strip_ns(child.tag), child


def _resolution_to_minutes(iso_duration: str) -> int:
    # ENTSO-E uses ISO 8601 durations like PT60M, PT15M, PT30M
    if iso_duration.startswith("PT") and iso_duration.endswith("M"):
        return int(iso_duration[2:-1])
    if iso_duration.startswith("PT") and iso_duration.endswith("H"):
        return int(iso_duration[2:-1]) * 60
    raise ValueError(f"Unsupported resolution format: {iso_duration}")


class EntsoeClient:
    def __init__(self, api_key: str, session: requests.Session | None = None, max_retries: int = 3):
        if not api_key:
            raise ValueError("ENTSO-E API key is required")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.max_retries = max_retries

    def _get(self, params: dict) -> str:
        params = {**params, "securityToken": self.api_key}
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(BASE_URL, params=params, timeout=30)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 * attempt)
                continue

            if resp.status_code == 200:
                return resp.text

            if resp.status_code == 429:
                # Rate limited — back off and retry.
                time.sleep(5 * attempt)
                continue

            # ENTSO-E returns 400 with an Acknowledgement_MarketDocument body
            # when e.g. no data exists for the requested period — surface it.
            raise EntsoeApiError(
                f"ENTSO-E API error {resp.status_code} for params={params}: {resp.text[:500]}"
            )

        raise EntsoeApiError(f"ENTSO-E request failed after {self.max_retries} attempts: {last_exc}")

    def get_day_ahead_prices(self, zone: str, eic_code: str, period_start: datetime, period_end: datetime) -> list[PricePoint]:
        """
        Fetch day-ahead spot prices (document type A44) for a single bidding zone.

        period_start / period_end must be timezone-aware UTC datetimes.
        """
        params = {
            "documentType": "A44",
            "in_Domain": eic_code,
            "out_Domain": eic_code,
            "periodStart": period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": period_end.strftime("%Y%m%d%H%M"),
        }
        xml_text = self._get(params)
        return self._parse_price_xml(xml_text, zone)

    @staticmethod
    def _parse_price_xml(xml_text: str, zone: str) -> list[PricePoint]:
        root = ET.fromstring(xml_text)

        if _strip_ns(root.tag) == "Acknowledgement_MarketDocument":
            # No data for the requested window (common for "today" before
            # day-ahead prices are published, or weekends/holidays with gaps).
            return []

        points: list[PricePoint] = []
        for tag, timeseries in _local_iter(root):
            if tag != "TimeSeries":
                continue
            for tag2, period in _local_iter(timeseries):
                if tag2 != "Period":
                    continue

                period_start = None
                resolution_min = 60
                for tag3, child in _local_iter(period):
                    if tag3 == "timeInterval":
                        for tag4, ti_child in _local_iter(child):
                            if tag4 == "start":
                                period_start = datetime.strptime(
                                    ti_child.text, "%Y-%m-%dT%H:%MZ"
                                ).replace(tzinfo=timezone.utc)
                    elif tag3 == "resolution":
                        resolution_min = _resolution_to_minutes(child.text)

                if period_start is None:
                    continue

                for tag3, point in _local_iter(period):
                    if tag3 != "Point":
                        continue
                    position = None
                    price = None
                    for tag4, pchild in _local_iter(point):
                        if tag4 == "position":
                            position = int(pchild.text)
                        elif tag4 == "price.amount":
                            price = float(pchild.text)
                    if position is None or price is None:
                        continue
                    ts = period_start + timedelta(minutes=resolution_min * (position - 1))
                    points.append(PricePoint(zone=zone, timestamp_utc=ts, price_eur_mwh=price, resolution_min=resolution_min))

        return points
