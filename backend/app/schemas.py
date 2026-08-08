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

