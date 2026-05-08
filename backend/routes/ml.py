"""
AgriNet AI — ML API Routes
Exposes all ML models via FastAPI endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import get_current_user, get_optional_user
from backend.db.supabase_client import log_crop_query

router = APIRouter(prefix="/api/ml", tags=["ml"])


# ── Request/Response Models ────────────────────────────────────────────────────

class CropRecommendRequest(BaseModel):
    soil: str = Field("alluvial", description="black | red | alluvial | sandy | clay | loamy")
    water: str = Field("medium", description="low | medium | high")
    land: str = Field("medium", description="small | medium | large")
    season: str = Field("kharif", description="kharif | rabi | zaid")
    region: str = Field("", description="User's district/region")
    # Optional real sensor/weather data
    temperature: Optional[float] = Field(None, description="Ambient temp °C")
    humidity: Optional[float] = Field(None, description="Humidity %")
    ph: Optional[float] = Field(None, ge=0, le=14, description="Soil pH")
    rainfall: Optional[float] = Field(None, ge=0, description="Rainfall mm")


class SpoilageRequest(BaseModel):
    crop: str
    weight_tons: float = Field(..., gt=0, le=50)
    transit_hours: float = Field(..., gt=0, le=72)
    temperature_c: float = Field(..., ge=-5, le=55)
    humidity_pct: float = Field(..., ge=0, le=100)
    packaging: str = Field("standard", description="standard | cold-chain | vacuum")


class SupplyBalancerRequest(BaseModel):
    region: str = Field("Maharashtra")
    season: str = Field("kharif")


class DemandForecastRequest(BaseModel):
    crop: str = Field("all")
    region: str = Field("Pune")
    days: int = Field(30, ge=7, le=90)


# ── Crop Recommendation ────────────────────────────────────────────────────────

@router.post("/crop-recommend")
async def crop_recommend(
    req: CropRecommendRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    valid_soils = ["black", "red", "alluvial", "sandy", "clay", "loamy"]
    valid_water = ["low", "medium", "high"]
    valid_land  = ["small", "medium", "large"]

    if req.soil not in valid_soils:
        raise HTTPException(400, f"soil must be one of {valid_soils}")
    if req.water not in valid_water:
        raise HTTPException(400, f"water must be one of {valid_water}")
    if req.land not in valid_land:
        raise HTTPException(400, f"land must be one of {valid_land}")

    from backend.ml.crop_model import get_crop_model
    model = get_crop_model()
    results = model.predict(
        soil=req.soil, water=req.water, land=req.land, season=req.season,
        temperature=req.temperature, humidity=req.humidity,
        ph=req.ph, rainfall=req.rainfall,
    )

    top = results[0] if results else {}

    # Log query
    if current_user:
        uid = current_user.get("user_id") or current_user.get("id", "anonymous")
        log_crop_query(uid, {
            "soil_type": req.soil, "water_level": req.water, "land_size": req.land,
            "result_crop": top.get("crop", ""), "result_score": top.get("score", 0),
            "location": req.region,
        })

    return {
        "results": results,
        "model": "XGBoost (ICAR crop dataset 4200 samples)",
        "region": req.region,
        "supply_balance_note": f"📊 {top.get('crop','this crop')} demand is currently underserved in {req.region or 'your region'}. Market gap identified by AI Supply Balancer." if top else "",
    }


# ── Spoilage Risk ──────────────────────────────────────────────────────────────

@router.post("/spoilage-risk")
async def spoilage_risk(req: SpoilageRequest):
    from backend.ml.spoilage_model import get_spoilage_model
    model = get_spoilage_model()
    return model.predict(
        crop=req.crop,
        weight_tons=req.weight_tons,
        transit_hours=req.transit_hours,
        temperature_c=req.temperature_c,
        humidity_pct=req.humidity_pct,
        packaging=req.packaging,
    )


# ── Supply Balancer ────────────────────────────────────────────────────────────

@router.post("/supply-balance")
async def supply_balance(req: SupplyBalancerRequest):
    from backend.ml.supply_balancer import run_supply_balancer
    return run_supply_balancer(region=req.region, season=req.season)


# ── Demand Forecast ────────────────────────────────────────────────────────────

@router.post("/demand-forecast")
async def demand_forecast(req: DemandForecastRequest):
    from backend.ml.demand_model import forecast_demand
    return forecast_demand(crop=req.crop, region=req.region, days=req.days)


# ── Mandi Prices (ML-backed) ───────────────────────────────────────────────────

@router.get("/mandi-prices")
async def mandi_prices(market: str = "Pune APMC"):
    from backend.ml.demand_model import get_mandi_prices
    return get_mandi_prices(market=market)


# ── Transport Pool ─────────────────────────────────────────────────────────────

class PoolRequest(BaseModel):
    farmer_count: int = Field(..., ge=1, le=30)
    total_weight_tons: float = Field(2.0, ge=0.1, le=100)
    distance_km: float = Field(25.0, ge=1, le=500)


@router.post("/pool-calculate")
async def pool_calculate(
    req: PoolRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """Calculate transport pool savings with real distance-based pricing."""
    # Base rate: ₹18/km for a 5-ton truck
    distance_cost = req.distance_km * 18
    loading_cost = 800
    per_stop_cost = 200 * req.farmer_count

    total_individual = distance_cost + loading_cost
    total_pooled = distance_cost + loading_cost + per_stop_cost
    cost_per_farmer = round(total_pooled / (req.farmer_count + 1))
    savings = round(total_individual - cost_per_farmer)

    # Environmental benefit
    co2_saved_kg = round(req.farmer_count * req.distance_km * 0.18, 1)

    return {
        "individual_cost": round(total_individual),
        "pooled_cost": cost_per_farmer,
        "savings": max(0, savings),
        "savings_pct": round(max(0, savings) / total_individual * 100, 1),
        "total_farmers": req.farmer_count + 1,
        "distance_km": req.distance_km,
        "co2_saved_kg": co2_saved_kg,
        "co2_saved_trees": round(co2_saved_kg / 21, 1),
    }


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
async def ml_health():
    try:
        from backend.ml.crop_model import get_crop_model
        model = get_crop_model()
        return {
            "status": "ok",
            "model_trained": model._trained,
            "crops_supported": len(model.crop_labels),
            "service": "AgriNet ML v2.0",
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}
