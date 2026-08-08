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
    mae_eur_mwh: float | None = None
    rmse_eur_mwh: float | None = None
    r2: float | None = None
    n_test: int | None = None


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ModelInfo(BaseModel):
    trained_at: str
    n_training_rows: int
    metrics: ModelMetrics
    feature_importances: list[FeatureImportance]
    zone_categories: list[str]

