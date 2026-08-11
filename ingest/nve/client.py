"""
NVE API clients:
  - Magasinstatistikk: Norway's official weekly reservoir fill level data.
  - Vannkraft-/vindkraftdatabase: hydro and wind power plant registries,
    used here to find projects under construction or with a granted
    concession (not yet in operation) — the actual capacity pipeline per
    price area, for the "consequence of not building out in time"
    discussion.

All three are public APIs, no key required.

Endpoints:
  - https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData
    (confirmed live 2026-08, incl. handling the 'VASS' area type NVE mixes
    into the response alongside the 'EL'/'NO' ones we track)
  - https://api.nve.no/web/Powerplant/GetHydroPowerPlants (confirmed live
    2026-08: includes plants under construction, not just operational
    ones — status is exposed via boolean flags, not a decodable status
    string, see PLANT_UNDER_CONSTRUCTION_BOOL_CANDIDATES below)
  - https://api.nve.no/web/WindPowerplant/GetWindPowerPlantsInOperation
    (confirmed live 2026-08 — this is the ONLY wind endpoint NVE's public
    API documentation (api.nve.no/doc/vindkraftdatabase/) exposes, and it
    really does only cover operational plants: no status field of any
    kind is present in its rows. There is currently no way to get
    under-construction/concession-granted wind capacity from NVE's API —
    this is a confirmed gap, not an unconfirmed guess.)

Field names for the two plant endpoints above were confirmed against live
responses 2026-08 (with real-world test data provided by a user testing
locally) — see the PLANT_*_CANDIDATES lists below for the exact fields
used, with unverified guesses kept only as fallbacks. Every parser here
still validates its assumptions and raises a clear NveApiError showing the
actual keys/values it found if something doesn't match, rather than
silently mis-mapping data, in case NVE changes the schema later.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

BASE_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
HYDRO_PLANTS_URL = "https://api.nve.no/web/Powerplant/GetHydroPowerPlants"
WIND_PLANTS_URL = "https://api.nve.no/web/WindPowerplant/GetWindPowerPlantsInOperation"

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


@dataclass
class PlantPipelineEntry:
    plant_id: str
    name: str
    status: str
    municipality: str | None
    county: str | None
    installed_effect_mw: float | None
    expected_commissioning: date | None
    elspot_zone: str | None  # e.g. 'NO3', straight from NVE's ElspotomraadeNummer — confirmed live, prefer over county mapping


def _iso_week_monday_utc(year: int, week: int) -> datetime:
    d = date.fromisocalendar(year, week, 1)  # ISO weekday 1 = Monday
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _parse_loose_date(value) -> date | None:
    """
    Handles the commissioning field being a full date string, an ISO
    datetime, or just a year (int/str). NVE uses sentinel values for
    "not set" instead of null — confirmed live to include -1 as a year,
    and '0001-01-01...' has shown up elsewhere in NVE responses (see
    reservoir parsing) — so anything outside a plausible year range is
    treated as "no date" rather than raising.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        year = int(value)
        return date(year, 1, 1) if 1900 <= year <= 2100 else None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit() and len(text) == 4:
        year = int(text)
        return date(year, 1, 1) if 1900 <= year <= 2100 else None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(text[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
        return parsed if parsed.year >= 1900 else None
    return None


# Candidate JSON key names per value, tried in order. Confirmed live against
# GetHydroPowerPlants and GetWindPowerPlantsInOperation (see comments below)
# — candidates not seen live are kept as fallbacks in case NVE's other
# plant-type endpoints (not yet queried) use different names.
#
# Live hydro (GetHydroPowerPlants) fields include: VannKraftverkID, Navn,
# Kraftverkstatus, UnderBygging, ErIDrift, UteAvDrift, Fylke, Kommune,
# MaksYtelse, ElspotomraadeNummer, SPSone, ForsteUtnyttelseAvFalletDato,
# IDriftDato, ...
#
# Live wind (GetWindPowerPlantsInOperation) fields include: VindkraftAnleggId,
# Navn, Fylke, Kommune, InstallertEffekt_MW, ElspotomraadeNummer,
# IdriftsettelseForsteByggetrinn, ... — notably NO status field at all,
# confirming this endpoint really does only cover operational plants (see
# get_wind_capacity_pipeline docstring).
PLANT_ID_CANDIDATES = ["VannKraftverkID", "VindkraftAnleggId", "VannkraftverkNr", "VindkraftverkNr", "AnleggNr", "Nr", "Id", "ID"]
PLANT_NAME_CANDIDATES = ["Navn", "Name", "VerkNavn", "AnleggNavn"]
PLANT_STATUS_CANDIDATES = ["Kraftverkstatus", "Status", "StatusVerk", "Konsesjonsstatus", "AnleggsStatus"]
PLANT_MUNICIPALITY_CANDIDATES = ["Kommune", "KommuneNavn", "Municipality"]
PLANT_COUNTY_CANDIDATES = ["Fylke", "FylkeNavn", "County"]
# Elspot bidding zone, reported directly as a number (1-5) — confirmed live
# on BOTH endpoints. Preferred over the county->zone approximation in
# nve/zones.py whenever present.
PLANT_ELSPOT_ZONE_CANDIDATES = ["ElspotomraadeNummer", "SPSone"]
PLANT_EFFECT_MW_CANDIDATES = [
    "MaksYtelse",  # hydro, confirmed live
    "InstallertEffekt_MW",  # wind, confirmed live
    "PaInstallertEffekt_MW",
    "SystemMaksYtelse",
    "Effekt_MW",
    "EffektMW",
    "InstalledCapacityMW",
]
PLANT_COMMISSIONING_CANDIDATES = [
    "IdriftsettelseForsteByggetrinn",  # wind, confirmed live
    "ForsteUtnyttelseAvFalletDato",  # hydro, confirmed live (approximate — "first use of the falls")
    "ForventetIdriftsettelse",
    "PlanlagtIdriftsettelse",
    "IdriftAar",
    "IdriftsattAar",
    "ExpectedCommissioning",
]

# Boolean flags confirmed live on the hydro endpoint — a much more reliable
# signal than string-matching a status field whose value coding (e.g. what
# Kraftverkstatus's raw values actually mean) isn't documented anywhere we
# could verify. Used in preference to PIPELINE_STATUS_SUBSTRINGS whenever
# present; falls back to string matching for endpoints that don't have
# these flags.
PLANT_UNDER_CONSTRUCTION_BOOL_CANDIDATES = ["UnderBygging"]
PLANT_IN_OPERATION_BOOL_CANDIDATES = ["ErIDrift"]
PLANT_OUT_OF_OPERATION_BOOL_CANDIDATES = ["UteAvDrift"]

# Status text values that mean "not yet operational, but committed" —
# matched by case-insensitive substring, not exact string, so small
# wording variations don't silently fall through as "unmatched". Only used
# as a fallback when none of the boolean flags above are present.
PIPELINE_STATUS_SUBSTRINGS = ["bygging", "konsesjon"]
# ...but never count a project already in the "avslått" (rejected) bucket,
# even if its status string also happens to contain "konsesjon" somewhere
# (e.g. "konsesjon avslått").
REJECTED_STATUS_SUBSTRINGS = ["avslå", "avslag", "trukket", "henlagt"]


def _first_present(row: dict, candidates: list[str]):
    for key in candidates:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("true", "1", "ja", "yes")


def _is_pipeline_status(status: str) -> bool:
    s = status.lower()
    if any(bad in s for bad in REJECTED_STATUS_SUBSTRINGS):
        return False
    return any(good in s for good in PIPELINE_STATUS_SUBSTRINGS)


def _pipeline_flag_and_status(row: dict) -> tuple[bool, str] | None:
    """
    Returns (is_pipeline, display_status) for a plant row, or None if the
    row has neither the boolean flags nor a recognizable status field —
    meaning this endpoint just doesn't expose the info we need (e.g. the
    wind "in operation only" endpoint).
    """
    under_construction_raw = _first_present(row, PLANT_UNDER_CONSTRUCTION_BOOL_CANDIDATES)
    if under_construction_raw is not None:
        under_construction = _as_bool(under_construction_raw)
        in_operation = _as_bool(_first_present(row, PLANT_IN_OPERATION_BOOL_CANDIDATES) or False)
        out_of_operation = _as_bool(_first_present(row, PLANT_OUT_OF_OPERATION_BOOL_CANDIDATES) or False)
        is_pipeline = under_construction and not in_operation and not out_of_operation
        return is_pipeline, ("Under bygging" if under_construction else "Ikke under bygging")

    status = _first_present(row, PLANT_STATUS_CANDIDATES)
    if status is not None:
        return _is_pipeline_status(str(status)), str(status)

    return None


def _elspot_zone_from_row(row: dict) -> str | None:
    raw = _first_present(row, PLANT_ELSPOT_ZONE_CANDIDATES)
    if raw is None:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    return f"NO{n}" if 1 <= n <= 5 else None


class NveClient:
    def __init__(self, session: requests.Session | None = None, max_retries: int = 3):
        self.session = session or requests.Session()
        self.max_retries = max_retries

    def _get(self, url: str = BASE_URL) -> list[dict]:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, timeout=60)
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

    def get_hydro_capacity_pipeline(self) -> list[PlantPipelineEntry]:
        """
        Hydro power plants under construction (not yet in operation), from
        NVE's hydro power plant database. Confirmed live to use boolean
        flags (UnderBygging/ErIDrift/UteAvDrift) rather than a decodable
        status string — see _pipeline_flag_and_status. Note: no confirmed
        way to separately identify "concession granted, construction not
        yet started" for hydro from this endpoint — only "under
        construction" is reliably detected.
        """
        rows = self._get(HYDRO_PLANTS_URL)
        return self._parse_plant_rows(rows)

    def get_wind_capacity_pipeline(self) -> list[PlantPipelineEntry]:
        """
        Confirmed live 2026-08 to always return an empty list: NVE's
        public API (api.nve.no/doc/vindkraftdatabase/) only exposes
        GetWindPowerPlantsInOperation for wind, whose rows have no status
        field of any kind — checked directly against NVE's own API
        documentation that no broader endpoint exists. There is currently
        no way to get under-construction/concession-granted wind capacity
        from NVE's API; this is a confirmed gap, not an open question.

        Still makes the real HTTP call (rather than short-circuiting to
        `[]`) so a cron run surfaces it if the endpoint goes down, and
        picks up automatically if NVE ever adds status data here.
        """
        rows = self._get(WIND_PLANTS_URL)
        return self._parse_plant_rows(rows)

    @classmethod
    def _parse_plant_rows(cls, rows: list[dict]) -> list[PlantPipelineEntry]:
        if not rows:
            return []

        first = rows[0]
        if _first_present(first, PLANT_ID_CANDIDATES) is None or _first_present(first, PLANT_NAME_CANDIDATES) is None:
            raise NveApiError(
                f"NVE plant response schema doesn't match expected fields — no id/name field found "
                f"among candidates {PLANT_ID_CANDIDATES} / {PLANT_NAME_CANDIDATES}. "
                f"Actual keys in first row: {sorted(first.keys())}. "
                f"Update the PLANT_*_CANDIDATES lists in nve/client.py to match."
            )

        entries: list[PlantPipelineEntry] = []
        for row in rows:
            flag_and_status = _pipeline_flag_and_status(row)
            if flag_and_status is None:
                # No status info at all in this row (e.g. the wind
                # "in operation only" endpoint) — not a schema error, just
                # means this endpoint can't tell us anything pipeline-wise.
                continue
            is_pipeline, status = flag_and_status
            if not is_pipeline:
                continue

            plant_id = _first_present(row, PLANT_ID_CANDIDATES)
            name = _first_present(row, PLANT_NAME_CANDIDATES)
            if plant_id is None or name is None:
                raise NveApiError(
                    f"NVE plant row has a pipeline status ('{status}') but is missing an id/name field. "
                    f"Row keys: {sorted(row.keys())}"
                )

            effect_raw = _first_present(row, PLANT_EFFECT_MW_CANDIDATES)
            commissioning_raw = _first_present(row, PLANT_COMMISSIONING_CANDIDATES)

            entries.append(
                PlantPipelineEntry(
                    plant_id=str(plant_id),
                    name=str(name),
                    status=str(status),
                    municipality=_first_present(row, PLANT_MUNICIPALITY_CANDIDATES),
                    county=_first_present(row, PLANT_COUNTY_CANDIDATES),
                    installed_effect_mw=float(effect_raw) if effect_raw is not None else None,
                    expected_commissioning=_parse_loose_date(commissioning_raw),
                    elspot_zone=_elspot_zone_from_row(row),
                )
            )

        return entries

    @staticmethod
    def _zone_from_row(row: dict) -> str | None:
        """
        Returns None (skip this row) for area types we don't track — NVE's
        Magasinstatistikk feed mixes several parallel regional breakdowns
        in one response, confirmed live: 'EL' (elspot bidding zone, paired
        with a numeric omrnr 1-5), 'NO' (national aggregate), and also
        'VASS' (vassdragsområde / hydrological catchment area — a finer,
        unrelated regional split NVE also publishes here). We only want
        EL and NO; anything else is silently skipped rather than treated
        as a schema error, since NVE may add further area types over time.
        """
        area_type = row.get(FIELD_AREA_TYPE)
        if area_type == "EL":
            return f"NO{row[FIELD_AREA_NR]}"
        if area_type == "NO":
            return "NO"
        return None

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
                if zone is None:
                    continue
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
