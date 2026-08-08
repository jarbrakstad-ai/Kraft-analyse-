"""
Bidding zone metadata exposed by the API.

Kept in sync by hand with ingest/entsoe/zones.py — the backend only needs
the human-readable names, not the EIC codes used for fetching.
"""

ZONE_NAMES = {
    "NO1": "Oslo / Øst-Norge",
    "NO2": "Kristiansand / Sør-Norge",
    "NO3": "Trondheim / Midt-Norge",
    "NO4": "Tromsø / Nord-Norge",
    "NO5": "Bergen / Vest-Norge",
    "DE_LU": "Tyskland / Luxembourg",
    "DK1": "Danmark (vest)",
    "DK2": "Danmark (øst)",
    "NL": "Nederland",
    "SE3": "Sverige (Stockholm)",
    "GB": "Storbritannia",  # only used for North Sea Link flow, no price/production ingest
    "NO": "Norge (hele landet)",  # national aggregate, only used for reservoir fill
}

VALID_ZONES = list(ZONE_NAMES.keys())

NORWEGIAN_ZONES = ["NO1", "NO2", "NO3", "NO4", "NO5"]
# European zones we actually ingest production/consumption for — "EU" here
# means this tracked set, not all of Europe. GB is excluded: it's only
# used for North Sea Link flow, with no production/consumption ingest.
EUROPEAN_TRACKED_ZONES = ["DE_LU", "DK1", "DK2", "NL", "SE3"]

# Pseudo-zone codes accepted by the /deficit endpoints for a summed view
# across a group of real zones, e.g. "NO" = NO1..NO5 combined.
AGGREGATE_ZONE_GROUPS = {
    "NO": NORWEGIAN_ZONES,
    "EU": EUROPEAN_TRACKED_ZONES,
}


def validate_zone(zone: str) -> str:
    from fastapi import HTTPException

    if zone not in VALID_ZONES:
        raise HTTPException(status_code=404, detail=f"Unknown zone '{zone}'. Valid zones: {VALID_ZONES}")
    return zone


def validate_zone_or_aggregate(zone: str) -> str:
    """Like validate_zone, but also accepts aggregate codes ('NO', 'EU') used by /deficit."""
    from fastapi import HTTPException

    if zone in AGGREGATE_ZONE_GROUPS or zone in VALID_ZONES:
        return zone
    raise HTTPException(
        status_code=404,
        detail=f"Unknown zone '{zone}'. Valid zones: {VALID_ZONES}, or aggregates: {list(AGGREGATE_ZONE_GROUPS.keys())}",
    )
