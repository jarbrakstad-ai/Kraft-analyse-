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
}

VALID_ZONES = list(ZONE_NAMES.keys())


def validate_zone(zone: str) -> str:
    from fastapi import HTTPException

    if zone not in VALID_ZONES:
        raise HTTPException(status_code=404, detail=f"Unknown zone '{zone}'. Valid zones: {VALID_ZONES}")
    return zone
