"""
AgriNet AI — Real Weather Routes
Uses OpenWeatherMap API with 10-min caching in Supabase/SQLite.
Falls back to realistic simulated data if API key not set.
"""

import os
import time
import random
from datetime import datetime
from typing import Optional
import httpx

from fastapi import APIRouter, Query, HTTPException
from backend.config import get_settings
from backend.db.supabase_client import get_weather_cache, set_weather_cache

settings = get_settings()
router = APIRouter(prefix="/api/weather", tags=["weather"])

OWM_BASE = "https://api.openweathermap.org/data/2.5"
OWM_GEO  = "https://api.openweathermap.org/geo/1.0"

# ── Realistic fallback weather by season ─────────────────────────────────────
_MONTHS_WEATHER = {
    range(3, 6):  dict(temp=36, humidity=28, desc="Hot & dry", icon="🌞", rain=0),       # Mar-May: Summer
    range(6, 10): dict(temp=29, humidity=82, desc="Monsoon", icon="🌧️", rain=12),         # Jun-Sep: Monsoon
    range(10, 12):dict(temp=26, humidity=55, desc="Post-monsoon", icon="⛅", rain=2),      # Oct-Nov: Kharif harvest
    range(12, 13):dict(temp=18, humidity=48, desc="Cool & clear", icon="🌤️", rain=0),     # Dec
    range(1, 3):  dict(temp=20, humidity=52, desc="Winter", icon="🌤️", rain=0),           # Jan-Feb: Rabi season
}

def _seasonal_fallback(lat: float = 19.0, lon: float = 74.0) -> dict:
    month = datetime.now().month
    for month_range, data in _MONTHS_WEATHER.items():
        if month in month_range:
            noise = random.uniform(-2, 2)
            return {
                "temperature_c": round(data["temp"] + noise, 1),
                "feels_like_c": round(data["temp"] + noise - 2, 1),
                "humidity_pct": data["humidity"] + random.randint(-5, 5),
                "rainfall_mm": data["rain"],
                "wind_kmh": round(random.uniform(8, 22), 1),
                "description": data["desc"],
                "icon": data["icon"],
                "condition_code": 800,
                "visibility_km": 10,
                "pressure_hpa": 1013,
                "uv_index": 6,
                "forecast_3d": _seasonal_forecast(month),
                "alert": _seasonal_alert(month),
                "source": "simulated",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
                "lat": lat, "lon": lon,
            }
    return _seasonal_fallback()

def _seasonal_forecast(month: int) -> str:
    if month in (6, 7, 8, 9):
        return "Heavy rain expected this week — harvest Kharif crops soon"
    if month in (3, 4, 5):
        return "Heat wave possible — irrigate morning/evening only"
    if month in (11, 12, 1, 2):
        return "Clear skies ahead — ideal for Rabi sowing"
    return "Partly cloudy — mild conditions expected"

def _seasonal_alert(month: int) -> Optional[str]:
    if month == 6:
        return "🌧️ Monsoon onset — protect stored produce from moisture"
    if month in (4, 5):
        return "🌡️ Heat advisory — avoid midday fieldwork"
    return None


async def _fetch_owm_current(lat: float, lon: float) -> dict:
    """Fetch real weather from OpenWeatherMap."""
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(f"{OWM_BASE}/weather", params={
            "lat": lat, "lon": lon,
            "appid": settings.openweathermap_key,
            "units": "metric",
        })
        r.raise_for_status()
        d = r.json()

        # 5-day forecast (3hr intervals)
        f = await client.get(f"{OWM_BASE}/forecast", params={
            "lat": lat, "lon": lon,
            "appid": settings.openweathermap_key,
            "units": "metric",
            "cnt": 8,
        })
        forecast_data = f.json() if f.status_code == 200 else {"list": []}

    main = d.get("main", {})
    wind = d.get("wind", {})
    weather = d.get("weather", [{}])[0]
    rain = d.get("rain", {}).get("1h", 0)

    # Map OWM icon to emoji
    icon_map = {
        "01": "☀️", "02": "🌤️", "03": "⛅", "04": "☁️",
        "09": "🌧️", "10": "🌦️", "11": "⛈️", "13": "❄️", "50": "🌫️",
    }
    icon_code = weather.get("icon", "01d")[:2]
    emoji = icon_map.get(icon_code, "🌡️")

    # Build 3-day forecast summary from hourly data
    forecast_items = forecast_data.get("list", [])
    daily_highs = {}
    for item in forecast_items:
        day = datetime.fromtimestamp(item["dt"]).strftime("%a")
        temp = item["main"]["temp"]
        if day not in daily_highs or temp > daily_highs[day]["temp"]:
            daily_highs[day] = {
                "temp": temp,
                "desc": item["weather"][0]["description"].title(),
                "rain": item.get("pop", 0) * 100,
            }
    forecast_3d_list = [{"day": k, **v} for k, v in list(daily_highs.items())[:3]]

    alert = None
    if main.get("temp", 0) > 40:
        alert = "🌡️ Heat wave warning — avoid midday fieldwork"
    elif rain > 20:
        alert = "⚠️ Heavy rainfall — protect harvested produce"

    return {
        "temperature_c": round(main.get("temp", 28), 1),
        "feels_like_c": round(main.get("feels_like", 28), 1),
        "humidity_pct": main.get("humidity", 65),
        "rainfall_mm": round(rain, 1),
        "wind_kmh": round(wind.get("speed", 10) * 3.6, 1),
        "description": weather.get("description", "").title(),
        "icon": emoji,
        "condition_code": weather.get("id", 800),
        "visibility_km": round(d.get("visibility", 10000) / 1000, 1),
        "pressure_hpa": main.get("pressure", 1013),
        "uv_index": None,  # requires separate OWM endpoint
        "forecast_3d": forecast_3d_list,
        "forecast_text": _seasonal_forecast(datetime.now().month),
        "alert": alert,
        "source": "openweathermap",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "lat": lat, "lon": lon,
        "city": d.get("name", ""),
        "country": d.get("sys", {}).get("country", "IN"),
    }


@router.get("/current")
async def get_weather(
    lat: float = Query(19.0, ge=-90, le=90),
    lon: float = Query(74.7, ge=-180, le=180),
):
    """Get real-time weather for a lat/lon. Cached for 10 minutes."""
    cache_key = f"weather_{round(lat,2)}_{round(lon,2)}"

    # Check cache
    cached = get_weather_cache(cache_key, ttl_seconds=600)
    if cached:
        cached["from_cache"] = True
        return cached

    # Try real API
    if settings.has_weather_api:
        try:
            data = await _fetch_owm_current(lat, lon)
            set_weather_cache(cache_key, data)
            return data
        except Exception as e:
            print(f"[Weather] OWM API error: {e}. Using fallback.")

    # Fallback
    data = _seasonal_fallback(lat, lon)
    return data


@router.get("/agri-advice")
async def get_agri_advice(
    lat: float = Query(19.0),
    lon: float = Query(74.7),
    crop: str = Query(""),
):
    """AI farming advice based on current weather conditions."""
    weather = await get_weather(lat, lon)
    temp = weather.get("temperature_c", 28)
    humidity = weather.get("humidity_pct", 65)
    rain = weather.get("rainfall_mm", 0)

    advice = []

    if temp > 38:
        advice.append("🌡️ Extreme heat: Irrigate in early morning (5–7am) and evening (6–8pm) only. Mulch soil to retain moisture.")
    elif temp > 30:
        advice.append("☀️ High temperature: Increase irrigation frequency. Monitor crops for heat stress signs.")

    if humidity > 80 and rain > 5:
        advice.append("🍄 High humidity + rain: Risk of fungal diseases (blight, mildew). Apply preventive fungicide on susceptible crops.")
    if rain > 50:
        advice.append("🌧️ Heavy rainfall: Check field drainage. Avoid chemical spraying until 48h after rain.")

    if crop.lower() in ("tomato", "टमाटर"):
        if temp > 35:
            advice.append("🍅 Tomato tip: Temperatures above 35°C cause flower drop. Provide shade nets if possible.")
        if humidity > 75:
            advice.append("🍅 Tomato tip: Spray copper fungicide to prevent early blight in high humidity.")

    if not advice:
        advice.append("✅ Weather conditions are favorable. Continue normal farming practices.")

    return {
        "weather": weather,
        "agri_advice": advice,
        "best_spray_time": "Early morning (6–9am) — low wind, high absorption" if temp < 30 else "Evening (5–7pm) after temperature drops",
        "irrigation_schedule": f"{'Every day' if temp > 35 else 'Every 2 days'} — {round(temp * 0.4 + 5, 1)}mm per irrigation recommended",
    }
