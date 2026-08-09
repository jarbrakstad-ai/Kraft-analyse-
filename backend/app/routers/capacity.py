from fastapi import APIRouter, Query

from ..db import get_cursor
from ..schemas import CapacityPipeline, PipelinePlant, PipelineZoneSummary
from ..zones import NORWEGIAN_ZONES

router = APIRouter(prefix="/capacity", tags=["capacity"])

# Jobs-per-MW coefficients for wind, land-based. Two separate phases —
# temporary construction jobs and permanent operational jobs — not one
# combined number, since conflating a one-off construction headcount with
# an ongoing operational headcount would misrepresent both.
#
# - Construction: an 80 MW wind project has been reported to create 100+
#   jobs during the build phase => ~1.25 jobs/MW, temporary.
# - Operation: experience-based figure of roughly 1 person-year per 15 MW
#   installed => ~0.067 jobs/MW, permanent, varies a lot plant to plant.
#
# No equivalent published figures were found for hydro, so hydro plants
# get no jobs estimate rather than a guessed one. None of this is
# independently verified against NVE's primary source (nve.no was blocked
# in the environment this was built in) — treat both as rough estimates,
# not precise or audited counts.
WIND_CONSTRUCTION_JOBS_PER_MW = 100 / 80  # ~1.25
WIND_OPERATION_JOBS_PER_MW = 1 / 15  # ~0.067
JOBS_ESTIMATE_NOTE = (
    "Anslåtte arbeidsplasser er kun beregnet for vindkraft, i to separate faser: "
    f"~{WIND_CONSTRUCTION_JOBS_PER_MW:.2f} midlertidige arbeidsplasser per MW under bygging, og "
    f"~{WIND_OPERATION_JOBS_PER_MW:.2f} permanente arbeidsplasser per MW i drift. Ingen tilsvarende tall er "
    "funnet for vannkraft. Begge tallene er grove erfaringsbaserte anslag (ikke NVE-tall verifisert mot "
    "primærkilde i dette miljøet) og varierer mye fra anlegg til anlegg."
)


def _is_under_construction(status: str) -> bool:
    return "bygging" in status.lower()


def _estimated_construction_jobs(source_type: str, installed_effect_mw: float | None) -> float | None:
    if source_type != "wind" or installed_effect_mw is None:
        return None
    return installed_effect_mw * WIND_CONSTRUCTION_JOBS_PER_MW


def _estimated_operation_jobs(source_type: str, installed_effect_mw: float | None) -> float | None:
    if source_type != "wind" or installed_effect_mw is None:
        return None
    return installed_effect_mw * WIND_OPERATION_JOBS_PER_MW


@router.get("/pipeline", response_model=CapacityPipeline)
def get_capacity_pipeline(
    zone: str | None = Query(None, description="Filter to one NO1-NO5 zone. Omit for all zones."),
):
    """
    Hydro and wind power plants under construction or with a granted
    concession (not yet in operation), from NVE's power plant databases —
    the actual capacity buildout pipeline per price area. A fact feed, not
    a forecast: it says what's already committed, not what's needed.

    zone is a best-effort mapping from the county NVE reports (see
    ingest/nve/zones.py) — plants whose county couldn't be mapped are
    still counted in unmapped_effect_mw so the totals aren't silently
    understated, but aren't attributable to a specific zone.
    """
    query = "SELECT * FROM capacity_pipeline"
    params: dict = {}
    if zone is not None:
        query += " WHERE zone = %(zone)s"
        params["zone"] = zone
    query += " ORDER BY zone NULLS LAST, installed_effect_mw DESC NULLS LAST"

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    plants = [
        PipelinePlant(
            **row,
            estimated_construction_jobs=_estimated_construction_jobs(row["source_type"], row["installed_effect_mw"]),
            estimated_operation_jobs=_estimated_operation_jobs(row["source_type"], row["installed_effect_mw"]),
        )
        for row in rows
    ]

    zones_to_report = [zone] if zone else NORWEGIAN_ZONES
    summaries = []
    for z in zones_to_report:
        zone_plants = [p for p in plants if p.zone == z]
        under_construction = sum(p.installed_effect_mw or 0 for p in zone_plants if _is_under_construction(p.status))
        concession_granted = sum(p.installed_effect_mw or 0 for p in zone_plants if not _is_under_construction(p.status))
        summaries.append(
            PipelineZoneSummary(
                zone=z,
                total_effect_mw=under_construction + concession_granted,
                under_construction_mw=under_construction,
                concession_granted_mw=concession_granted,
                n_plants=len(zone_plants),
                estimated_construction_jobs=sum(p.estimated_construction_jobs or 0 for p in zone_plants),
                estimated_operation_jobs=sum(p.estimated_operation_jobs or 0 for p in zone_plants),
            )
        )

    unmapped_effect_mw = sum(p.installed_effect_mw or 0 for p in plants if p.zone is None)

    # National jobs totals are always over ALL plants in the table,
    # regardless of the `zone` query filter above — a separate, unfiltered
    # query so filtering to one zone doesn't silently mislabel that zone's
    # total as "national". Also includes zone=NULL (unmapped-county)
    # plants, which the per-zone summaries above can't attribute anywhere.
    with get_cursor() as cur:
        cur.execute("SELECT source_type, installed_effect_mw FROM capacity_pipeline")
        all_rows = cur.fetchall()
    national_estimated_construction_jobs = sum(
        _estimated_construction_jobs(r["source_type"], r["installed_effect_mw"]) or 0 for r in all_rows
    )
    national_estimated_operation_jobs = sum(
        _estimated_operation_jobs(r["source_type"], r["installed_effect_mw"]) or 0 for r in all_rows
    )

    with get_cursor() as cur:
        cur.execute("SELECT max(inserted_at) AS last_updated FROM capacity_pipeline")
        row = cur.fetchone()
        last_updated = row["last_updated"] if row else None

    return CapacityPipeline(
        zones=summaries,
        unmapped_effect_mw=unmapped_effect_mw,
        national_estimated_construction_jobs=national_estimated_construction_jobs,
        national_estimated_operation_jobs=national_estimated_operation_jobs,
        plants=plants,
        last_updated=last_updated,
        jobs_estimate_note=JOBS_ESTIMATE_NOTE,
    )
