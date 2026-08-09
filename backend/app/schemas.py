from datetime import date, datetime

from pydantic import BaseModel


class ZoneInfo(BaseModel):
    code: str
    name: str


class PricePoint(BaseModel):
    zone: str
    timestamp_utc: datetime
    price_eur_mwh: float
    resolution_min: int


class LatestPrice(BaseModel):
    zone: str
    timestamp_utc: datetime
    price_eur_mwh: float


class DailyAverage(BaseModel):
    zone: str
    day: date
    avg_price_eur_mwh: float
    min_price_eur_mwh: float
    max_price_eur_mwh: float


class ProductionPoint(BaseModel):
    zone: str
    timestamp_utc: datetime
    production_type: str
    quantity_mw: float


class LatestProduction(BaseModel):
    zone: str
    production_type: str
    timestamp_utc: datetime
    quantity_mw: float


class ProductionMixShare(BaseModel):
    zone: str
    production_type: str
    avg_quantity_mw: float
    share_percent: float


class InterconnectorInfo(BaseModel):
    name: str
    from_zone: str
    to_zone: str


class FlowPoint(BaseModel):
    from_zone: str
    to_zone: str
    interconnector: str | None
    timestamp_utc: datetime
    flow_mw: float


class LatestFlow(BaseModel):
    from_zone: str
    to_zone: str
    interconnector: str | None
    timestamp_utc: datetime
    flow_mw: float


class FlowDailyAverage(BaseModel):
    from_zone: str
    to_zone: str
    interconnector: str | None
    day: date
    avg_flow_mw: float


class ReservoirPoint(BaseModel):
    zone: str
    week_start_utc: datetime
    fill_percent: float
    capacity_gwh: float | None


class LatestReservoir(BaseModel):
    zone: str
    week_start_utc: datetime
    fill_percent: float


class WeatherPoint(BaseModel):
    zone: str
    station_id: str
    timestamp_utc: datetime
    temperature_c: float | None
    wind_speed_ms: float | None
    precipitation_mm: float | None


class LatestWeather(BaseModel):
    zone: str
    station_id: str
    timestamp_utc: datetime
    temperature_c: float | None
    wind_speed_ms: float | None
    precipitation_mm: float | None


class PriceProductionPoint(BaseModel):
    timestamp_utc: datetime
    price_eur_mwh: float
    quantity_mw: float


class PriceProductionCorrelation(BaseModel):
    zone: str
    production_type: str
    n: int
    pearson_r: float | None
    points: list[PriceProductionPoint]


class PriceReservoirPoint(BaseModel):
    week_start_utc: datetime
    avg_price_eur_mwh: float
    fill_percent: float


class PriceReservoirCorrelation(BaseModel):
    zone: str
    n: int
    pearson_r: float | None
    points: list[PriceReservoirPoint]


class PriceSpreadFlowPoint(BaseModel):
    timestamp_utc: datetime
    price_spread_eur_mwh: float
    net_flow_mw: float


class PriceSpreadFlowCorrelation(BaseModel):
    zone_a: str
    zone_b: str
    n: int
    pearson_r: float | None
    points: list[PriceSpreadFlowPoint]


class PriceWeatherPoint(BaseModel):
    timestamp_utc: datetime
    price_eur_mwh: float
    weather_value: float


class PriceWeatherCorrelation(BaseModel):
    zone: str
    weather_variable: str
    n: int
    pearson_r: float | None
    points: list[PriceWeatherPoint]


class ProductionWeatherPoint(BaseModel):
    timestamp_utc: datetime
    quantity_mw: float
    weather_value: float


class ProductionWeatherCorrelation(BaseModel):
    zone: str
    production_type: str
    weather_variable: str
    n: int
    pearson_r: float | None
    points: list[ProductionWeatherPoint]


class PricePrediction(BaseModel):
    zone: str
    based_on_day: date
    predicted_date: date
    predicted_avg_price_eur_mwh: float
    missing_features: list[str]
    model_trained_at: str


class ModelMetrics(BaseModel):
    """Holdout metrics. Unit depends on the model: EUR/MWh for price, MW for deficit — see ModelInfo.metric_unit."""

    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None
    n_test: int | None = None


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ModelInfo(BaseModel):
    trained_at: str
    n_training_rows: int
    metric_unit: str
    metrics: ModelMetrics
    feature_importances: list[FeatureImportance]
    zone_categories: list[str]


class ConsumptionPoint(BaseModel):
    zone: str
    timestamp_utc: datetime
    load_mw: float


class LatestConsumption(BaseModel):
    zone: str
    timestamp_utc: datetime
    load_mw: float


class BalancePoint(BaseModel):
    timestamp_utc: datetime
    production_mw: float
    load_mw: float
    balance_mw: float


class DeficitSummary(BaseModel):
    zone: str
    n: int
    avg_balance_mw: float
    hours_in_deficit: int
    points: list[BalancePoint]


class DeficitForecastZone(BaseModel):
    zone: str
    predicted_balance_mw: float
    based_on_production_mw: float | None
    based_on_load_mw: float | None
    missing_features: list[str]


class DeficitForecast(BaseModel):
    zone: str
    based_on_day: date
    predicted_date: date
    predicted_balance_mw: float
    is_aggregate: bool
    zone_breakdown: list[DeficitForecastZone]
    model_trained_at: str


class ScenarioYear(BaseModel):
    year: int
    production_mw: float
    load_mw: float
    balance_mw: float


class ScenarioForecast(BaseModel):
    """
    A deterministic what-if projection, NOT a trained model prediction.
    Baseline production/consumption (averaged over baseline_days) is
    compounded forward at the given yearly growth rates. Useful for
    exploring "what if demand grows N% per year" scenarios 1-5 years out
    — a horizon far too long for the day-ahead ML model to say anything
    meaningful about.
    """

    zone: str
    baseline_days: int
    baseline_production_mw: float
    baseline_load_mw: float
    consumption_growth_pct_per_year: float
    production_growth_pct_per_year: float
    years: list[ScenarioYear]


class PipelinePlant(BaseModel):
    source_type: str  # 'hydro' | 'wind'
    plant_id: str
    name: str
    status: str
    municipality: str | None
    county: str | None
    zone: str | None
    installed_effect_mw: float | None
    expected_commissioning: date | None
    estimated_jobs: float | None  # rough estimate, wind only — see CapacityPipeline.jobs_estimate_note


class PipelineZoneSummary(BaseModel):
    """
    Total effect (MW) under construction or with a granted concession in a
    zone, from NVE's power plant registries — a fact feed, not a forecast.
    See /capacity/pipeline/model-info-equivalent caveats in the docs: the
    NVE field mapping is unverified against a live response, and wind
    coverage may be incomplete (see ingest/nve/client.py).
    """

    zone: str
    total_effect_mw: float
    under_construction_mw: float
    concession_granted_mw: float
    n_plants: int
    estimated_jobs: float  # sum of PipelinePlant.estimated_jobs for this zone (0 if none/hydro-only)


class CapacityPipeline(BaseModel):
    zones: list[PipelineZoneSummary]
    unmapped_effect_mw: float  # sum for plants whose county couldn't be mapped to a zone
    national_estimated_jobs: float  # sum of estimated_jobs over ALL plants, incl. zone=NULL ones
    plants: list[PipelinePlant]
    last_updated: datetime | None
    jobs_estimate_note: str

