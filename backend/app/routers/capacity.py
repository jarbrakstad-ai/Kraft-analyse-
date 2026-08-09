from fastapi import APIRouter, Query

from ..db import get_cursor
from ..schemas import CapacityPipeline, PipelinePlant, PipelineZoneSummary
from ..zones import NORWEGIAN_ZONES

router = APIRouter(prefix="/capacity", tags=["capacity"])

# Jobs-per-MW coefficient for wind, from NVE's "Verdiskapning" analysis of
# land-based wind power: employment in a county rose by 0.48 jobs per newly
# installed MW. This is a COMBINED figure covering both building and
# operating the plant — not construction-phase jobs alone and not
# operational jobs alone, but the two summed. No equivalent published
# figure was found for hydro, so hydro plants get no jobs estimate rather
# than a guessed one. Still not independently verified against the primary
# NVE source (nve.no was blocked in the environment this was built in) —
# treat it as a rough estimate, not a precise or audited count.
WIND_JOBS_PER_MW = 0.48
JOBS_ESTIMATE_NOTE = (
    "Anslåtte arbeidsplasser er kun beregnet for vindkraft, basert på NVEs publiserte anslag "
    f"({WIND_JOBS_PER_MW} arbeidsplasser per ny installert MW i et fylke). Ingen tilsvarende tall er "
    "funnet for vannkraft. Tallet er en samlet sysselsettingseffekt av både å bygge og drifte kraftverket "
    "— ikke kun anleggsfasen og ikke kun driftsfasen alene — og bør uansett behandles som et grovt anslag, "
    "ikke en presist målt sysselsettingseffekt."
)


def _is_under_construction(status: str) -> bool:
    return "bygging" in status.lower()


def _estimated_jobs(source_type: str, installed_effect_mw: float | None) -> float | None:
    if source_type != "wind" or installed_effect_mw is None:
        return None
    return installed_effect_mw * WIND_JOBS_PER_MW


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
        PipelinePlant(**row, estimated_jobs=_estimated_jobs(row["source_type"], row["installed_effect_mw"]))
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
                estimated_jobs=sum(p.estimated_jobs or 0 for p in zone_plants),
            )
        )

    unmapped_effect_mw = sum(p.installed_effect_mw or 0 for p in plants if p.zone is None)

    with get_cursor() as cur:
        cur.execute("SELECT max(inserted_at) AS last_updated FROM capacity_pipeline")
        row = cur.fetchone()
        last_updated = row["last_updated"] if row else None

    return CapacityPipeline(
        zones=summaries,
        unmapped_effect_mw=unmapped_effect_mw,
        plants=plants,
        last_updated=last_updated,
        jobs_estimate_note=JOBS_ESTIMATE_NOTE,
    )
