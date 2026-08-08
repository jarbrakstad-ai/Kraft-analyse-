"""
ENTSO-E bidding zone / EIC domain codes.

Full reference: https://www.entsoe.eu/data/energy-identification-codes-eic/eic-area-codes-map/
Add more zones here as the dashboard grows (e.g. SE1/SE2/SE4, FI, PL, GB).
"""

ZONES = {
    # Norway
    "NO1": "10YNO-1--------2",   # Oslo / Øst-Norge
    "NO2": "10YNO-2--------T",   # Kristiansand / Sør-Norge
    "NO3": "10YNO-3--------J",   # Trondheim / Midt-Norge
    "NO4": "10YNO-4--------9",   # Tromsø / Nord-Norge
    "NO5": "10Y1001A1001A48H",   # Bergen / Vest-Norge
    # Europe (selected)
    "DE_LU": "10Y1001A1001A82H",  # Germany + Luxembourg bidding zone
    "DK1": "10YDK-1--------W",
    "DK2": "10YDK-2--------M",
    "NL": "10YNL----------L",
    "SE3": "10Y1001A1001A46L",   # Stockholm — most relevant SE zone for NO cable analysis
}

DEFAULT_ZONES = list(ZONES.keys())
