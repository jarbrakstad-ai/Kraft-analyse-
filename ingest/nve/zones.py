"""
Best-effort county (fylke) -> NVE elspot price zone mapping.

NVE's power plant databases report a municipality/county, not a bidding
zone directly. This maps the 2024 county structure to the zone that county
falls in for *most* of its area — it is a coarse approximation, not an
authoritative boundary:

- A handful of municipalities near a zone border genuinely belong to a
  different zone than the rest of their county (bidding zones don't follow
  county lines exactly). Innlandet is the biggest known case: most of it is
  NO1, but a few northern/western municipalities are actually NO3/NO5.
- Zone boundaries have occasionally been redrawn; this reflects the zones
  as of when this mapping was written.

Treat `zone` values derived from this mapping as indicative, not precise —
good enough for "which price area has projects in the pipeline", not for
anything that needs municipality-level accuracy. If NVE's API turns out to
report a zone/elspot area directly (unconfirmed — see client.py), prefer
that over this mapping.
"""

FYLKE_TO_ZONE = {
    "Oslo": "NO1",
    "Akershus": "NO1",
    "Østfold": "NO1",
    "Viken": "NO1",  # pre-2024 fylke name, kept for older API responses
    "Innlandet": "NO1",  # approximation — a few northern kommuner are actually NO3
    "Buskerud": "NO1",
    "Vestfold": "NO1",
    "Telemark": "NO2",
    "Vestfold og Telemark": "NO2",
    "Agder": "NO2",
    "Aust-Agder": "NO2",
    "Vest-Agder": "NO2",
    "Rogaland": "NO2",
    "Vestland": "NO5",
    "Hordaland": "NO5",
    "Sogn og Fjordane": "NO5",
    "Møre og Romsdal": "NO3",
    "Trøndelag": "NO3",
    "Trööndelage": "NO3",
    "Nordland": "NO4",
    "Troms": "NO4",
    "Finnmark": "NO4",
    "Troms og Finnmark": "NO4",
    "Romsa ja Finnmárku": "NO4",
}


def zone_from_county(county: str | None) -> str | None:
    """Returns the best-effort NO1-NO5 zone for a county name, or None if unknown/unmapped."""
    if not county:
        return None
    return FYLKE_TO_ZONE.get(county.strip())
