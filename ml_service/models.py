"""
AgriNet ML Service — Pydantic request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


# ===== Crop Recommendation =====

class CropRecommendRequest(BaseModel):
    soil: str = Field(..., description="Soil type: black | red | alluvial | sandy | clay")
    water: str = Field(..., description="Water availability: low | medium | high")
    land: str = Field(..., description="Land size: small | medium | large")
    region: Optional[str] = Field("Nashik", description="Region/district name")
    season: Optional[str] = Field("kharif", description="Season: kharif | rabi | zaid")


class CropResult(BaseModel):
    crop: str
    score: float
    match: str
    profit: str
    reason: str
    confidence: float
    feature_importance: dict


class CropRecommendResponse(BaseModel):
    results: List[CropResult]
    model: str
    region: str
    supply_balance_note: Optional[str] = None


# ===== Demand Forecast =====

class DemandForecastRequest(BaseModel):
    crop: Optional[str] = Field("all", description="Crop to forecast, or 'all'")
    region: Optional[str] = Field("Pune", description="Target market")
    days: Optional[int] = Field(30, description="Days to forecast")


class CropForecast(BaseModel):
    crop: str
    trend: float           # percent change
    current_price: int     # ₹/kg
    forecast_price: int    # ₹/kg
    demand_index: float    # 0–100
    confidence: float


class DemandForecastResponse(BaseModel):
    region: str
    forecasts: List[CropForecast]
    model: str
    data_sources: List[str]


# ===== Supply Balancer =====

class SupplyBalancerRequest(BaseModel):
    region: Optional[str] = Field("Maharashtra", description="State/region")


class VillageAssignment(BaseModel):
    village: str
    assigned_crop: str
    reason: str
    overproduction_risk: float     # 0–1
    expected_profit: str
    market_distance_km: float


class SupplyBalancerResponse(BaseModel):
    region: str
    assignments: List[VillageAssignment]
    model: str
    balance_score: float           # 0–100, how well-balanced the supply is


# ===== Mandi Prices =====

class MandiPrice(BaseModel):
    crop: str
    price_per_kg: int
    market: str
    trend: str           # up | down | stable
    week_change: float   # percent


class MandiPricesResponse(BaseModel):
    market: str
    prices: List[MandiPrice]
    weather: dict
    updated_at: str


# ===== Spoilage Risk =====

class SpoilageRequest(BaseModel):
    crop: str
    weight_tons: float
    transit_hours: float
    temperature_c: float
    humidity_pct: float


class SpoilageResponse(BaseModel):
    crop: str
    risk_score: float       # 0–100
    risk_level: str         # low | medium | high | critical
    confidence: float
    suggestions: List[str]
    model: str
