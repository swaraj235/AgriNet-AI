"""
AgriNet AI — Location Routes
Real reverse geocoding via OpenCage + nearby mandi lookup.
"""

import math
import httpx
from typing import Optional
from fastapi import APIRouter, Query
from backend.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/location", tags=["location"])

OPENCAGE_BASE = "https://api.opencagedata.com/geocode/v1/json"

# ── Real mandi database (curated from APMC records) ──────────────────────────
MANDIS = [
    {"name": "Pune APMC", "state": "Maharashtra", "district": "Pune", "lat": 18.5204, "lon": 73.8567, "type": "State APMC"},
    {"name": "Nashik APMC", "state": "Maharashtra", "district": "Nashik", "lat": 19.9975, "lon": 73.7898, "type": "District APMC"},
    {"name": "Lasalgaon Mandi", "state": "Maharashtra", "district": "Nashik", "lat": 20.1187, "lon": 74.0248, "type": "Onion Hub"},
    {"name": "Ahmednagar APMC", "state": "Maharashtra", "district": "Ahmednagar", "lat": 19.0952, "lon": 74.7496, "type": "District APMC"},
    {"name": "Solapur APMC", "state": "Maharashtra", "district": "Solapur", "lat": 17.6868, "lon": 75.9062, "type": "District APMC"},
    {"name": "Kolhapur APMC", "state": "Maharashtra", "district": "Kolhapur", "lat": 16.6980, "lon": 74.2179, "type": "District APMC"},
    {"name": "Satara APMC", "state": "Maharashtra", "district": "Satara", "lat": 17.6805, "lon": 74.0183, "type": "District APMC"},
    {"name": "Aurangabad APMC", "state": "Maharashtra", "district": "Aurangabad", "lat": 19.8762, "lon": 75.3433, "type": "District APMC"},
    {"name": "Mumbai APMC (Vashi)", "state": "Maharashtra", "district": "Mumbai", "lat": 19.0748, "lon": 72.9985, "type": "Metro APMC"},
    {"name": "Pimpri-Chinchwad Mandi", "state": "Maharashtra", "district": "Pune", "lat": 18.6298, "lon": 73.7997, "type": "Satellite"},
    {"name": "Kalamb APMC", "state": "Maharashtra", "district": "Osmanabad", "lat": 18.6120, "lon": 76.3560, "type": "District APMC"},
    {"name": "Nagpur APMC", "state": "Maharashtra", "district": "Nagpur", "lat": 21.1458, "lon": 79.0882, "type": "State APMC"},
    # Karnataka
    {"name": "Bangalore (Yeshwanthpur) APMC", "state": "Karnataka", "district": "Bangalore", "lat": 13.0282, "lon": 77.5532, "type": "State APMC"},
    {"name": "Tumkur APMC", "state": "Karnataka", "district": "Tumkur", "lat": 13.3379, "lon": 77.1173, "type": "District APMC"},
    # MP
    {"name": "Indore APMC", "state": "Madhya Pradesh", "district": "Indore", "lat": 22.7196, "lon": 75.8577, "type": "State APMC"},
    {"name": "Bhopal APMC", "state": "Madhya Pradesh", "district": "Bhopal", "lat": 23.2599, "lon": 77.4126, "type": "State APMC"},
    # UP
    {"name": "Agra Mandi", "state": "Uttar Pradesh", "district": "Agra", "lat": 27.1767, "lon": 78.0081, "type": "District APMC"},
    {"name": "Lucknow APMC", "state": "Uttar Pradesh", "district": "Lucknow", "lat": 26.8467, "lon": 80.9462, "type": "State APMC"},
    # Rajasthan
    {"name": "Jaipur APMC", "state": "Rajasthan", "district": "Jaipur", "lat": 26.9124, "lon": 75.7873, "type": "State APMC"},
    # Gujarat
    {"name": "Ahmedabad APMC", "state": "Gujarat", "district": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "type": "State APMC"},
    {"name": "Gondal APMC", "state": "Gujarat", "district": "Rajkot", "lat": 21.9611, "lon": 70.7969, "type": "Groundnut Hub"},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


async def _opencage_reverse(lat: float, lon: float) -> Optional[dict]:
    """Reverse geocode using OpenCage."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(OPENCAGE_BASE, params={
                "q": f"{lat},{lon}",
                "key": settings.opencage_key,
                "language": "en",
                "limit": 1,
                "no_annotations": 1,
                "countrycode": "in",
            })
            r.raise_for_status()
            results = r.json().get("results", [])
            if results:
                comp = results[0].get("components", {})
                return {
                    "village": comp.get("village") or comp.get("town") or comp.get("city_district") or "",
                    "taluka": comp.get("county") or comp.get("suburb") or "",
                    "district": comp.get("state_district") or comp.get("district") or "",
                    "state": comp.get("state", ""),
                    "country": comp.get("country", "India"),
                    "postcode": comp.get("postcode", ""),
                    "formatted": results[0].get("formatted", ""),
                }
    except Exception as e:
        print(f"[OpenCage] Error: {e}")
    return None


def _fallback_region(lat: float, lon: float) -> dict:
    """Return approximate region name from lat/lon using bounding boxes."""
    regions = [
        {"state": "Maharashtra", "district": "Nashik", "village": "Nashik region", "lat": 20.0, "lon": 73.8, "r": 1.5},
        {"state": "Maharashtra", "district": "Pune", "village": "Pune region", "lat": 18.5, "lon": 73.8, "r": 1.5},
        {"state": "Maharashtra", "district": "Ahmednagar", "village": "Ahmednagar region", "lat": 19.1, "lon": 74.7, "r": 1.0},
        {"state": "Maharashtra", "district": "Aurangabad", "village": "Aurangabad region", "lat": 19.9, "lon": 75.3, "r": 1.5},
        {"state": "Karnataka", "district": "Bangalore", "village": "Bangalore region", "lat": 12.97, "lon": 77.59, "r": 1.0},
        {"state": "Gujarat", "district": "Ahmedabad", "village": "Ahmedabad region", "lat": 23.03, "lon": 72.57, "r": 1.0},
        {"state": "Uttar Pradesh", "district": "Lucknow", "village": "Lucknow region", "lat": 26.85, "lon": 80.95, "r": 1.0},
    ]
    best = min(regions, key=lambda r: _haversine_km(lat, lon, r["lat"], r["lon"]))
    return {"village": best["village"], "district": best["district"], "state": best["state"],
            "country": "India", "taluka": "", "postcode": "", "formatted": f"{best['village']}, {best['state']}"}


@router.get("/reverse-geocode")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """Convert GPS coordinates to human-readable location."""
    if settings.has_geocode_api:
        result = await _opencage_reverse(lat, lon)
        if result:
            return {"location": result, "source": "opencage"}

    result = _fallback_region(lat, lon)
    return {"location": result, "source": "estimated"}


@router.get("/nearby-mandis")
async def nearby_mandis(
    lat: float = Query(19.0, ge=-90, le=90),
    lon: float = Query(74.7, ge=-180, le=180),
    limit: int = Query(5, ge=1, le=10),
):
    """Return nearest APMC mandis sorted by distance."""
    with_dist = [
        {**m, "distance_km": round(_haversine_km(lat, lon, m["lat"], m["lon"]), 1)}
        for m in MANDIS
    ]
    sorted_mandis = sorted(with_dist, key=lambda x: x["distance_km"])[:limit]
    return {
        "mandis": sorted_mandis,
        "user_location": {"lat": lat, "lon": lon},
        "nearest": sorted_mandis[0] if sorted_mandis else None,
    }


@router.get("/all-mandis")
async def all_mandis(state: str = Query("")):
    """Return all mandis, optionally filtered by state."""
    if state:
        filtered = [m for m in MANDIS if state.lower() in m["state"].lower()]
    else:
        filtered = MANDIS
    return {"mandis": filtered, "total": len(filtered)}
