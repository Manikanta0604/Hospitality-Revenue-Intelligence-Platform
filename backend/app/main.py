from functools import lru_cache
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .analytics import breakdown, daily_trend, forecast, kpis, pricing
from .config import get_settings
from .models import ForecastPoint, Overview, PricingRecommendation
from .store import DataStore

settings = get_settings()
app = FastAPI(title="Hospitality Revenue Intelligence API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["*"], allow_headers=["*"])


@lru_cache
def store() -> DataStore:
    return DataStore(settings.data_path)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/overview", response_model=Overview)
def overview(data: DataStore = Depends(store)):
    frame = data.data
    return Overview(kpis=kpis(frame), trend=daily_trend(frame))


@app.get("/api/properties")
def properties(data: DataStore = Depends(store)):
    return breakdown(data.data, "property")


@app.get("/api/channels")
def channels(data: DataStore = Depends(store)):
    return breakdown(data.data, "channel")


@app.get("/api/forecast", response_model=list[ForecastPoint])
def get_forecast(days: int = Query(14, ge=1, le=90), data: DataStore = Depends(store)):
    return forecast(data.data, days)


@app.get("/api/pricing", response_model=list[PricingRecommendation])
def get_pricing(data: DataStore = Depends(store)):
    return pricing(data.data)


@app.post("/api/data/upload", status_code=201)
async def upload(file: UploadFile = File(...), data: DataStore = Depends(store)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a CSV file")
    try:
        rows = data.replace(await file.read())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"filename": file.filename, "rows": rows}
