"""
Interconnector metadata exposed by the API.

Kept in sync by hand with ingest/entsoe/interconnectors.py.
"""

INTERCONNECTORS = {
    "NorNed": ("NO2", "NL"),
    "NordLink": ("NO2", "DE_LU"),
    "North Sea Link": ("NO2", "GB"),
    "Skagerrak": ("NO2", "DK1"),
    "Kontiskan": ("SE3", "DK1"),
}

VALID_INTERCONNECTORS = list(INTERCONNECTORS.keys())


def validate_interconnector(name: str) -> str:
    from fastapi import HTTPException

    if name not in VALID_INTERCONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown interconnector '{name}'. Valid values: {VALID_INTERCONNECTORS}")
    return name
