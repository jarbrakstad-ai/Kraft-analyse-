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
