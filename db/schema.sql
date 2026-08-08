-- Kraft-analyse database schema
-- PostgreSQL + TimescaleDB
--
-- All time series tables share the pattern: zone + timestamp (UTC) + value(s).
-- Hypertables are created on the timestamp column for efficient time-range queries.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Day-ahead spot prices per bidding zone (EUR/MWh, as delivered by ENTSO-E)
CREATE TABLE IF NOT EXISTS spot_price (
    zone            TEXT        NOT NULL,      -- e.g. 'NO1', 'DE_LU', 'DK1', 'NL', 'SE3'
    timestamp_utc   TIMESTAMPTZ NOT NULL,       -- start of the delivery hour, UTC
    price_eur_mwh   DOUBLE PRECISION NOT NULL,
    resolution_min  INTEGER     NOT NULL DEFAULT 60,
    source          TEXT        NOT NULL DEFAULT 'entsoe',
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (zone, timestamp_utc, source)
);

SELECT create_hypertable('spot_price', 'timestamp_utc', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_spot_price_zone_time ON spot_price (zone, timestamp_utc DESC);

-- Production per source (hydro, wind, solar, thermal, ...) per zone
CREATE TABLE IF NOT EXISTS production_per_source (
    zone            TEXT        NOT NULL,
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    production_type TEXT        NOT NULL,       -- e.g. 'hydro', 'wind_onshore', 'solar', 'thermal_gas'
    quantity_mw     DOUBLE PRECISION NOT NULL,
    source          TEXT        NOT NULL DEFAULT 'entsoe',
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (zone, timestamp_utc, production_type, source)
);

SELECT create_hypertable('production_per_source', 'timestamp_utc', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_prod_zone_time ON production_per_source (zone, timestamp_utc DESC);

-- Cross-zonal physical flow (import/export) on interconnectors
CREATE TABLE IF NOT EXISTS cross_border_flow (
    from_zone       TEXT        NOT NULL,
    to_zone         TEXT        NOT NULL,
    interconnector  TEXT,                       -- e.g. 'NordLink', 'NorNed', 'North Sea Link', 'Skagerrak', 'Kontiskan'
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    flow_mw         DOUBLE PRECISION NOT NULL,
    source          TEXT        NOT NULL DEFAULT 'entsoe',
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (from_zone, to_zone, timestamp_utc, source)
);

SELECT create_hypertable('cross_border_flow', 'timestamp_utc', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_flow_zones_time ON cross_border_flow (from_zone, to_zone, timestamp_utc DESC);

-- Reservoir (magasin) fill level, weekly figures per zone (NVE/Statnett convention)
CREATE TABLE IF NOT EXISTS reservoir_fill (
    zone            TEXT        NOT NULL,       -- e.g. 'NO1'..'NO5' or 'NO' for national
    week_start_utc  TIMESTAMPTZ NOT NULL,
    fill_percent    DOUBLE PRECISION NOT NULL,
    capacity_gwh    DOUBLE PRECISION,
    source          TEXT        NOT NULL DEFAULT 'statnett',
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (zone, week_start_utc, source)
);

SELECT create_hypertable('reservoir_fill', 'week_start_utc', if_not_exists => TRUE);

-- Consumption (load) per zone
CREATE TABLE IF NOT EXISTS consumption (
    zone            TEXT        NOT NULL,
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    load_mw         DOUBLE PRECISION NOT NULL,
    source          TEXT        NOT NULL DEFAULT 'entsoe',
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (zone, timestamp_utc, source)
);

SELECT create_hypertable('consumption', 'timestamp_utc', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_consumption_zone_time ON consumption (zone, timestamp_utc DESC);

-- Weather observations from one representative station per zone (MET Norway
-- Frost API). Explanatory variable for the analysis: temperature drives
-- heating demand, wind speed drives wind production, precipitation drives
-- hydro inflow and reservoir fill.
CREATE TABLE IF NOT EXISTS weather_observation (
    zone              TEXT        NOT NULL,     -- e.g. 'NO1'..'NO5'
    station_id        TEXT        NOT NULL,     -- MET Norway source ID, e.g. 'SN18700'
    timestamp_utc     TIMESTAMPTZ NOT NULL,
    temperature_c     DOUBLE PRECISION,
    wind_speed_ms     DOUBLE PRECISION,
    precipitation_mm  DOUBLE PRECISION,
    source            TEXT        NOT NULL DEFAULT 'met_frost',
    inserted_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (zone, timestamp_utc, source)
);

SELECT create_hypertable('weather_observation', 'timestamp_utc', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_weather_zone_time ON weather_observation (zone, timestamp_utc DESC);

-- Power plant capacity pipeline from NVE's hydro/wind power plant databases:
-- projects under construction or with a granted concession, not yet in
-- operation. Answers "how much expected effect increase is actually in the
-- pipeline per price area" for the kraftutbygging discussion — a plain fact
-- feed, not a forecast. `zone` is a best-effort mapping from the county NVE
-- reports (see ingest/nve/zones.py) and can be NULL when the county is
-- unknown or straddles a zone border; `county`/`municipality` are kept
-- as-is from NVE so nothing is lost if the zone mapping is wrong or missing.
CREATE TABLE IF NOT EXISTS capacity_pipeline (
    source_type             TEXT        NOT NULL,  -- 'hydro' | 'wind'
    plant_id                TEXT        NOT NULL,   -- NVE's own ID for the plant/project
    name                    TEXT        NOT NULL,
    status                  TEXT        NOT NULL,   -- raw NVE status string, e.g. 'Under bygging', 'Gitt konsesjon'
    municipality             TEXT,
    county                  TEXT,
    zone                    TEXT,                   -- best-effort NO1-NO5 mapping from county, may be NULL
    installed_effect_mw     DOUBLE PRECISION,
    expected_commissioning  DATE,
    source                  TEXT        NOT NULL DEFAULT 'nve',
    inserted_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_type, plant_id, source)
);

CREATE INDEX IF NOT EXISTS idx_capacity_pipeline_zone ON capacity_pipeline (zone);
