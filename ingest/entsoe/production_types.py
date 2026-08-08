"""
ENTSO-E PSR (Power System Resource) type codes -> our production_type slugs.

Reference: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_areas
(Appendix: "B" codes, table "Type_MarketAgreement.Type").
"""

PSR_TYPE_TO_PRODUCTION_TYPE = {
    "B01": "biomass",
    "B02": "thermal_coal",       # Fossil Brown coal/Lignite
    "B03": "thermal_gas",        # Fossil Coal-derived gas
    "B04": "thermal_gas",        # Fossil Gas
    "B05": "thermal_coal",       # Fossil Hard coal
    "B06": "thermal_oil",        # Fossil Oil
    "B07": "thermal_oil",        # Fossil Oil shale
    "B08": "thermal_other",      # Fossil Peat
    "B09": "other",              # Geothermal
    "B10": "hydro_pumped_storage",
    "B11": "hydro",              # Hydro Run-of-river and poundage
    "B12": "hydro",              # Hydro Water Reservoir
    "B13": "other",              # Marine
    "B14": "nuclear",
    "B15": "other_renewable",
    "B16": "solar",
    "B17": "waste",
    "B18": "wind_offshore",
    "B19": "wind_onshore",
    "B20": "other",
    "B25": "storage",            # Energy storage
}

# businessType A04 = "consumption" — used for e.g. pumped-storage pumping.
# We only want actual *generation*, so this is filtered out by the client.
CONSUMPTION_BUSINESS_TYPE = "A04"
