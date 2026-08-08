"""
Selected Norwegian interconnectors (utenlandskabler) and the bidding zone
pairs they connect, for cross-border physical flow ingest.

North Sea Link connects to Great Britain, which isn't otherwise used by the
price/production ingest — its EIC code is added here rather than in
zones.ZONES so it doesn't end up in DEFAULT_ZONES for those scripts.
"""

from .zones import ZONES

GB_EIC = "10YGB----------A"

# Zone -> EIC lookup covering everything the interconnectors below need.
INTERCONNECTOR_ZONE_EIC = {**ZONES, "GB": GB_EIC}

# name -> (zone_a, zone_b). Flow is fetched in both directions (a->b and
# b->a) since a cable can carry power either way depending on the hour.
INTERCONNECTORS = {
    "NorNed": ("NO2", "NL"),
    "NordLink": ("NO2", "DE_LU"),
    "North Sea Link": ("NO2", "GB"),
    "Skagerrak": ("NO2", "DK1"),
    "Kontiskan": ("SE3", "DK1"),
}
