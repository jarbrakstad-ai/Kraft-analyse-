"""
One representative MET Norway weather station per Norwegian bidding zone,
used to correlate weather with price/production/reservoir data.

Station IDs are MET Norway "SN" source IDs (https://frost.met.no/sources.html).
NOT verified against a live API response (see met/client.py docstring) —
double-check these against frost.met.no/sources.html?types=SensorSystem if
a fetch comes back empty for a zone.
"""

STATIONS = {
    "NO1": "SN18700",  # Oslo - Blindern
    "NO2": "SN39040",  # Kristiansand - Kjevik
    "NO3": "SN68860",  # Trondheim - Voll
    "NO4": "SN90450",  # Tromsø
    "NO5": "SN50540",  # Bergen - Florida
}

DEFAULT_ZONES = list(STATIONS.keys())
