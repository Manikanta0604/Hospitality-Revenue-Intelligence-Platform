from datetime import timedelta
import numpy as np
import pandas as pd
from .models import DailyPoint, ForecastPoint, KPIs, PricingRecommendation


REQUIRED_COLUMNS = {
    "date", "property", "channel", "rooms_available", "rooms_sold", "adr",
    "cancelled_bookings", "total_bookings", "lead_time_days", "event_index",
}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    clean = df.copy()
    clean["date"] = pd.to_datetime(clean["date"])
    numeric = list(REQUIRED_COLUMNS - {"date", "property", "channel"})
    clean[numeric] = clean[numeric].apply(pd.to_numeric, errors="raise")
    if (clean[["rooms_available", "rooms_sold", "adr"]].values < 0).any():
        raise ValueError("Room and rate values cannot be negative")
    return clean


def kpis(df: pd.DataFrame) -> KPIs:
    revenue = float((df.rooms_sold * df.adr).sum())
    sold = float(df.rooms_sold.sum())
    available = float(df.rooms_available.sum())
    bookings = float(df.total_bookings.sum())
    return KPIs(
        revenue=round(revenue, 2),
        occupancy=round(sold / available * 100, 1) if available else 0,
        adr=round(revenue / sold, 2) if sold else 0,
        revpar=round(revenue / available, 2) if available else 0,
        cancellation_rate=round(float(df.cancelled_bookings.sum()) / bookings * 100, 1) if bookings else 0,
    )


def daily_trend(df: pd.DataFrame) -> list[DailyPoint]:
    rows = []
    for day, group in df.groupby("date"):
        metric = kpis(group)
        rows.append(DailyPoint(date=day.date(), revenue=metric.revenue, occupancy=metric.occupancy, adr=metric.adr, revpar=metric.revpar))
    return rows


def breakdown(df: pd.DataFrame, dimension: str) -> list[dict]:
    result = []
    for key, group in df.groupby(dimension):
        result.append({dimension: str(key), **kpis(group).model_dump(), "rooms_sold": int(group.rooms_sold.sum())})
    return sorted(result, key=lambda item: item["revenue"], reverse=True)


def forecast(df: pd.DataFrame, days: int) -> list[ForecastPoint]:
    daily = df.groupby("date").agg({"rooms_sold": "sum", "rooms_available": "sum", "adr": "mean", "event_index": "mean"}).reset_index()
    x = np.arange(len(daily))
    slope, intercept = np.polyfit(x, daily.rooms_sold, 1) if len(daily) > 1 else (0, float(daily.rooms_sold.iloc[0]))
    weekday_factor = daily.assign(weekday=daily.date.dt.weekday).groupby("weekday").rooms_sold.mean() / daily.rooms_sold.mean()
    last = daily.date.max()
    available = int(daily.rooms_available.iloc[-1])
    adr = float(daily.adr.tail(3).mean())
    output = []
    for step in range(1, days + 1):
        target = last + timedelta(days=step)
        base = intercept + slope * (len(daily) - 1 + step)
        sold = max(0, min(available, int(round(base * float(weekday_factor.get(target.weekday(), 1))))))
        output.append(ForecastPoint(date=target.date(), rooms_sold=sold, revenue=round(sold * adr, 2), occupancy=round(sold / available * 100, 1) if available else 0))
    return output


def pricing(df: pd.DataFrame) -> list[PricingRecommendation]:
    recommendations = []
    for property_name, group in df.groupby("property"):
        current = float((group.rooms_sold * group.adr).sum() / group.rooms_sold.sum())
        occupancy = group.rooms_sold.sum() / group.rooms_available.sum()
        pace = group.tail(max(1, len(group) // 3)).rooms_sold.mean() / max(group.rooms_sold.mean(), 1)
        event = float(group.event_index.tail(2).mean())
        adjustment, reasons = 0.0, []
        if occupancy >= .85: adjustment += .10; reasons.append("Occupancy above 85%")
        elif occupancy < .60: adjustment -= .08; reasons.append("Occupancy below 60%")
        if pace > 1.05: adjustment += .05; reasons.append("Booking pace is accelerating")
        if event > 1.2: adjustment += .08; reasons.append("Elevated event demand")
        adjustment = max(-.15, min(.25, adjustment))
        recommendations.append(PricingRecommendation(property=property_name, current_adr=round(current, 2), recommended_rate=round(current * (1 + adjustment), 2), adjustment_percent=round(adjustment * 100, 1), reasons=reasons or ["Rate aligned with current demand"] ))
    return recommendations
