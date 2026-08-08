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

from .production_types import CONSUMPTION_BUSINESS_TYPE, PSR_TYPE_TO_PRODUCTION_TYPE

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


@dataclass
class ProductionPoint:
    zone: str
    timestamp_utc: datetime
    production_type: str
    quantity_mw: float
    resolution_min: int


@dataclass
class FlowPoint:
    from_zone: str
    to_zone: str
    timestamp_utc: datetime
    flow_mw: float
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

    def get_actual_generation_per_type(self, zone: str, eic_code: str, period_start: datetime, period_end: datetime) -> list[ProductionPoint]:
        """
        Fetch actual generation per production type (document type A75,
        process type A16 "Realised") for a single bidding zone.

        period_start / period_end must be timezone-aware UTC datetimes.
        """
        params = {
            "documentType": "A75",
            "processType": "A16",
            "in_Domain": eic_code,
            "periodStart": period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": period_end.strftime("%Y%m%d%H%M"),
        }
        xml_text = self._get(params)
        return self._parse_generation_xml(xml_text, zone)

    def get_cross_border_flow(
        self, from_zone: str, from_eic: str, to_zone: str, to_eic: str, period_start: datetime, period_end: datetime
    ) -> list[FlowPoint]:
        """
        Fetch physical flow (document type A11) from from_zone to to_zone.

        A cable can carry power in either direction depending on the hour,
        so the caller should fetch both directions (swap from/to) to get
        the full picture for an interconnector.
        """
        params = {
            "documentType": "A11",
            "out_Domain": from_eic,
            "in_Domain": to_eic,
            "periodStart": period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": period_end.strftime("%Y%m%d%H%M"),
        }
        xml_text = self._get(params)
        return self._parse_flow_xml(xml_text, from_zone, to_zone)

    @staticmethod
    def _parse_period(period: ET.Element) -> tuple[datetime | None, int, list[tuple[int, float]]]:
        """Parse a <Period> element into (period_start, resolution_min, [(position, value), ...])."""
        period_start = None
        resolution_min = 60
        for tag, child in _local_iter(period):
            if tag == "timeInterval":
                for tag2, ti_child in _local_iter(child):
                    if tag2 == "start":
                        period_start = datetime.strptime(ti_child.text, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
            elif tag == "resolution":
                resolution_min = _resolution_to_minutes(child.text)

        values: list[tuple[int, float]] = []
        for tag, point in _local_iter(period):
            if tag != "Point":
                continue
            position = None
            value = None
            for tag2, pchild in _local_iter(point):
                if tag2 == "position":
                    position = int(pchild.text)
                elif tag2 in ("price.amount", "quantity"):
                    value = float(pchild.text)
            if position is not None and value is not None:
                values.append((position, value))

        return period_start, resolution_min, values

    @classmethod
    def _parse_price_xml(cls, xml_text: str, zone: str) -> list[PricePoint]:
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
                period_start, resolution_min, values = cls._parse_period(period)
                if period_start is None:
                    continue
                for position, price in values:
                    ts = period_start + timedelta(minutes=resolution_min * (position - 1))
                    points.append(PricePoint(zone=zone, timestamp_utc=ts, price_eur_mwh=price, resolution_min=resolution_min))

        return points

    @classmethod
    def _parse_generation_xml(cls, xml_text: str, zone: str) -> list[ProductionPoint]:
        root = ET.fromstring(xml_text)

        if _strip_ns(root.tag) == "Acknowledgement_MarketDocument":
            return []

        points: list[ProductionPoint] = []
        for tag, timeseries in _local_iter(root):
            if tag != "TimeSeries":
                continue

            psr_type = None
            business_type = None
            period_elems = []
            for tag2, child in _local_iter(timeseries):
                if tag2 == "MktPSRType":
                    for tag3, psr_child in _local_iter(child):
                        if tag3 == "psrType":
                            psr_type = psr_child.text
                elif tag2 == "businessType":
                    business_type = child.text
                elif tag2 == "Period":
                    period_elems.append(child)

            if business_type == CONSUMPTION_BUSINESS_TYPE:
                # Pumped-storage pumping etc. — not generation, skip.
                continue

            production_type = PSR_TYPE_TO_PRODUCTION_TYPE.get(psr_type, psr_type or "unknown")

            for period in period_elems:
                period_start, resolution_min, values = cls._parse_period(period)
                if period_start is None:
                    continue
                for position, quantity in values:
                    ts = period_start + timedelta(minutes=resolution_min * (position - 1))
                    points.append(
                        ProductionPoint(
                            zone=zone,
                            timestamp_utc=ts,
                            production_type=production_type,
                            quantity_mw=quantity,
                            resolution_min=resolution_min,
                        )
                    )

        return points

    @classmethod
    def _parse_flow_xml(cls, xml_text: str, from_zone: str, to_zone: str) -> list[FlowPoint]:
        root = ET.fromstring(xml_text)

        if _strip_ns(root.tag) == "Acknowledgement_MarketDocument":
            # No flow data for the window — common for the direction that
            # didn't carry any power during the requested period.
            return []

        points: list[FlowPoint] = []
        for tag, timeseries in _local_iter(root):
            if tag != "TimeSeries":
                continue
            for tag2, period in _local_iter(timeseries):
                if tag2 != "Period":
                    continue
                period_start, resolution_min, values = cls._parse_period(period)
                if period_start is None:
                    continue
                for position, quantity in values:
                    ts = period_start + timedelta(minutes=resolution_min * (position - 1))
                    points.append(
                        FlowPoint(
                            from_zone=from_zone,
                            to_zone=to_zone,
                            timestamp_utc=ts,
                            flow_mw=quantity,
                            resolution_min=resolution_min,
                        )
                    )

        return points
