import pandas as pd
from app.analytics import forecast, kpis, pricing, validate


def frame():
    return validate(pd.DataFrame([
        {"date":"2026-01-01","property":"A","channel":"Direct","rooms_available":100,"rooms_sold":80,"adr":200,"cancelled_bookings":2,"total_bookings":20,"lead_time_days":10,"event_index":1.0},
        {"date":"2026-01-02","property":"A","channel":"OTA","rooms_available":100,"rooms_sold":90,"adr":220,"cancelled_bookings":1,"total_bookings":22,"lead_time_days":8,"event_index":1.3},
    ]))


def test_kpi_formulas():
    result = kpis(frame())
    assert result.occupancy == 85.0
    assert result.revenue == 35800.0


def test_forecast_length():
    assert len(forecast(frame(), 7)) == 7


def test_pricing_is_explainable():
    recommendation = pricing(frame())[0]
    assert recommendation.recommended_rate > recommendation.current_adr
    assert recommendation.reasons
