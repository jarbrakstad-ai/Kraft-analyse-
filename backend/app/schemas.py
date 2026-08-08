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

