"""
AgriNet ML Service — Time Series Demand Forecasting Model.
Simulates realistic mandi price time series using numpy.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional

# ===== Base Price Data (₹/kg) =====

CROP_PROFILES = {
    'Tomato': {
        'base_price': 18,
        'volatility': 0.22,
        'trend': 0.04,          # gentle upward trend
        'seasonality_amp': 8,   # festival demand spikes
        'demand_index': 87.0,
    },
    'Onion': {
        'base_price': 24,
        'volatility': 0.18,
        'trend': 0.02,
        'seasonality_amp': 5,
        'demand_index': 54.0,
    },
    'Potato': {
        'base_price': 14,
        'volatility': 0.12,
        'trend': 0.01,
        'seasonality_amp': 3,
        'demand_index': 43.0,
    },
    'Wheat': {
        'base_price': 22,
        'volatility': 0.08,
        'trend': 0.015,
        'seasonality_amp': 2,
        'demand_index': 18.0,
    },
    'Brinjal': {
        'base_price': 16,
        'volatility': 0.20,
        'trend': 0.03,
        'seasonality_amp': 4,
        'demand_index': 31.0,
    },
    'Soybean': {
        'base_price': 42,
        'volatility': 0.10,
        'trend': 0.025,
        'seasonality_amp': 3,
        'demand_index': 38.0,
    },
}

# ===== Weather Data Simulation =====

WEATHER_DATA = {
    'temperature_c': 28.4,
    'humidity_pct': 61,
    'rainfall_mm': 0.0,
    'condition': 'Partly cloudy',
    'forecast_3d': 'Light rain expected in 3 days',
    'alert': None
}


def _generate_price_series(crop: str, days: int = 30, seed: int = 42) -> list:
    """Generate a realistic price time series for a given crop."""
    np.random.seed(seed + hash(crop) % 100)
    profile = CROP_PROFILES.get(crop, CROP_PROFILES['Tomato'])

    prices = []
    price = float(profile['base_price'])

    for i in range(days):
        # Trend component
        price += price * profile['trend'] / 30
        # Seasonal component (festival spike mid-series)
        seasonal = profile['seasonality_amp'] * np.sin(2 * np.pi * i / days)
        # Random noise
        noise = np.random.normal(0, price * profile['volatility'] * 0.1)
        day_price = max(5, price + seasonal + noise)
        prices.append(round(day_price, 1))

    return prices


def forecast_demand(crop: Optional[str] = 'all', region: str = 'Pune', days: int = 30):
    """
    Return demand forecasts for one or all crops.
    """
    crops_to_forecast = list(CROP_PROFILES.keys()) if crop == 'all' else [crop]
    results = []

    for c in crops_to_forecast:
        if c not in CROP_PROFILES:
            continue

        profile = CROP_PROFILES[c]
        series = _generate_price_series(c, days)

        current_price = series[0]
        forecast_price = series[-1]
        trend_pct = round((forecast_price - current_price) / current_price * 100, 1)

        results.append({
            'crop': c,
            'trend': trend_pct,
            'current_price': int(current_price),
            'forecast_price': int(forecast_price),
            'demand_index': profile['demand_index'],
            'confidence': round(85 + np.random.uniform(-5, 5), 1),
            'price_series': [int(p) for p in series],  # for charting
        })

    return {
        'region': region,
        'forecasts': results,
        'model': 'ARIMA + Seasonal Decomposition (simulated)',
        'data_sources': [
            'Agmarknet Mandi Price API',
            'IMD Weather Data',
            'APMC Historical Records',
            'Festival Calendar Signals'
        ]
    }


def get_mandi_prices(market: str = 'Pune APMC'):
    """Return current simulated mandi prices with trend signals."""
    np.random.seed(int(datetime.now().hour))  # changes hourly for realism

    prices = []
    for crop, profile in CROP_PROFILES.items():
        noise = np.random.uniform(-2, 3)
        price = int(profile['base_price'] + noise)
        week_change = round(np.random.uniform(-8, 12), 1)
        trend = 'up' if week_change > 0 else ('down' if week_change < -2 else 'stable')

        prices.append({
            'crop': crop,
            'price_per_kg': price,
            'market': market,
            'trend': trend,
            'week_change': week_change,
        })

    # Sort by demand index (most sought after first)
    demand_order = {c: p['demand_index'] for c, p in CROP_PROFILES.items()}
    prices.sort(key=lambda x: demand_order.get(x['crop'], 0), reverse=True)

    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M IST')

    return {
        'market': market,
        'prices': prices,
        'weather': WEATHER_DATA,
        'updated_at': updated_at
    }
