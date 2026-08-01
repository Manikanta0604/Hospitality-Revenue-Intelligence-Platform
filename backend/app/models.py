from datetime import date
from pydantic import BaseModel


class KPIs(BaseModel):
    revenue: float
    occupancy: float
    adr: float
    revpar: float
    cancellation_rate: float


class DailyPoint(BaseModel):
    date: date
    revenue: float
    occupancy: float
    adr: float
    revpar: float


class Overview(BaseModel):
    kpis: KPIs
    trend: list[DailyPoint]


class ForecastPoint(BaseModel):
    date: date
    rooms_sold: int
    revenue: float
    occupancy: float


class PricingRecommendation(BaseModel):
    property: str
    current_adr: float
    recommended_rate: float
    adjustment_percent: float
    reasons: list[str]
