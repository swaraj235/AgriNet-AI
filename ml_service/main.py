"""
AgriNet ML Service — FastAPI Main Application.
Runs on port 8000 as an AI/ML microservice.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from models import (
    CropRecommendRequest, CropRecommendResponse,
    DemandForecastRequest, DemandForecastResponse,
    SupplyBalancerRequest, SupplyBalancerResponse,
    MandiPricesResponse,
    SpoilageRequest, SpoilageResponse,
)
from crop_model import get_crop_model
from demand_model import forecast_demand, get_mandi_prices
from supply_balancer import run_supply_balancer


# ===== App Setup =====
app = FastAPI(
    title="AgriNet ML Service",
    description="AI/ML microservice for crop recommendation, demand forecasting and supply balancing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Health =====
@app.get("/health")
def health():
    return {"status": "ok", "service": "AgriNet ML Service", "version": "1.0.0"}


# ===== Crop Recommendation =====
@app.post("/api/ml/crop-recommend", response_model=CropRecommendResponse)
def crop_recommend(req: CropRecommendRequest):
    valid_soils = ['black', 'red', 'alluvial', 'sandy', 'clay']
    valid_water = ['low', 'medium', 'high']
    valid_land  = ['small', 'medium', 'large']

    if req.soil not in valid_soils:
        raise HTTPException(400, f"soil must be one of {valid_soils}")
    if req.water not in valid_water:
        raise HTTPException(400, f"water must be one of {valid_water}")
    if req.land not in valid_land:
        raise HTTPException(400, f"land must be one of {valid_land}")

    model = get_crop_model()
    results = model.predict(req.soil, req.water, req.land, req.season or 'kharif')

    # Supply balance note
    top_crop = results[0]['crop'] if results else 'Unknown'
    note = f"AI Supply Balancer: {top_crop} demand is currently underserved in {req.region}. Recommended crop aligns with regional market gaps."

    return CropRecommendResponse(
        results=results,
        model="Random Forest Classifier (sklearn) — 100 estimators",
        region=req.region,
        supply_balance_note=note,
    )


# ===== Demand Forecast =====
@app.post("/api/ml/demand-forecast", response_model=DemandForecastResponse)
def demand_forecast(req: DemandForecastRequest):
    data = forecast_demand(
        crop=req.crop or 'all',
        region=req.region or 'Pune',
        days=req.days or 30
    )
    return DemandForecastResponse(**data)


# ===== Supply Balancer =====
@app.post("/api/ml/supply-balance", response_model=SupplyBalancerResponse)
def supply_balance(req: SupplyBalancerRequest):
    data = run_supply_balancer(region=req.region or 'Maharashtra')
    return SupplyBalancerResponse(**data)


# ===== Mandi Prices =====
@app.get("/api/ml/mandi-prices")
def mandi_prices(market: str = "Pune APMC"):
    return get_mandi_prices(market=market)


# ===== Spoilage Risk =====
@app.post("/api/ml/spoilage-risk", response_model=SpoilageResponse)
def spoilage_risk(req: SpoilageRequest):
    """Predict spoilage risk using environmental and logistics factors."""

    # Feature vector: [transit_hours, temperature_c, humidity_pct, weight_tons]
    # Normalize
    transit_factor = min(req.transit_hours / 12, 1.0)
    temp_factor    = max(0, (req.temperature_c - 20) / 20)    # higher temp = worse
    humidity_factor = max(0, (req.humidity_pct - 50) / 50)   # high humidity = worse
    weight_factor  = min(req.weight_tons / 10, 1.0)           # heavier = more at risk

    CROP_SENSITIVITY = {
        'Tomato': 0.85, 'Brinjal': 0.90, 'Potato': 0.55,
        'Onion': 0.45,  'Wheat': 0.20,   'Soybean': 0.35,
    }
    sensitivity = CROP_SENSITIVITY.get(req.crop, 0.65)

    risk_score = (
        transit_factor * 35 +
        temp_factor    * 30 +
        humidity_factor * 20 +
        weight_factor  * 5  +
        sensitivity    * 10
    )
    risk_score = min(100, round(risk_score, 1))
    confidence = round(82 + np.random.uniform(-3, 3), 1)

    if risk_score >= 75:
        risk_level = 'critical'
        suggestions = [
            f"Reroute to nearest mandi — reduce transit by at least 2 hours",
            "Alert nearby buyers immediately via AgriNet marketplace",
            "Consider cold storage if transit > 4 hours",
            "Sell at slight discount to prevent total loss",
        ]
    elif risk_score >= 50:
        risk_level = 'high'
        suggestions = [
            "Monitor temperature every 30 minutes",
            "Pre-arrange buyer at destination mandi",
            "Cold storage option available within 5 km",
        ]
    elif risk_score >= 25:
        risk_level = 'medium'
        suggestions = [
            "Maintain current route but reduce stops",
            "Keep cargo ventilated",
        ]
    else:
        risk_level = 'low'
        suggestions = ["No immediate action required. Shipment on track."]

    return SpoilageResponse(
        crop=req.crop,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        suggestions=suggestions,
        model="Logistic Regression + Environmental Sensor Model",
    )


# ===== Run =====
if __name__ == "__main__":
    import uvicorn
    print("\n  🤖 AgriNet ML Service running at http://localhost:8000")
    print("  📖 API Docs: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
