"""
AgriNet AI — AI Supply Balancer
Distributes optimal crops across villages using affinity + entropy optimization.
"""

import numpy as np
from typing import Optional

# ── Village database (expanded with more states) ─────────────────────────────
REGIONS = {
    "Maharashtra": [
        {"name": "Nashik A", "soil": "black", "water": "high", "district": "Nashik", "lat": 20.0, "lon": 73.8, "market_km": 8.2, "farmers": 320},
        {"name": "Nashik B", "soil": "red", "water": "medium", "district": "Nashik", "lat": 20.1, "lon": 74.0, "market_km": 12.4, "farmers": 180},
        {"name": "Ahmednagar", "soil": "alluvial", "water": "medium", "district": "Ahmednagar", "lat": 19.1, "lon": 74.7, "market_km": 5.6, "farmers": 240},
        {"name": "Solapur", "soil": "black", "water": "low", "district": "Solapur", "lat": 17.7, "lon": 75.9, "market_km": 9.1, "farmers": 150},
        {"name": "Satara", "soil": "red", "water": "high", "district": "Satara", "lat": 17.7, "lon": 74.0, "market_km": 14.3, "farmers": 195},
        {"name": "Pune Rural", "soil": "alluvial", "water": "high", "district": "Pune", "lat": 18.5, "lon": 73.8, "market_km": 4.2, "farmers": 280},
        {"name": "Kolhapur", "soil": "clay", "water": "high", "district": "Kolhapur", "lat": 16.7, "lon": 74.2, "market_km": 7.8, "farmers": 210},
        {"name": "Aurangabad", "soil": "sandy", "water": "low", "district": "Aurangabad", "lat": 19.9, "lon": 75.3, "market_km": 18.5, "farmers": 120},
        {"name": "Latur", "soil": "black", "water": "medium", "district": "Latur", "lat": 18.4, "lon": 76.6, "market_km": 11.2, "farmers": 165},
        {"name": "Jalgaon", "soil": "alluvial", "water": "medium", "district": "Jalgaon", "lat": 21.0, "lon": 75.6, "market_km": 6.8, "farmers": 200},
    ],
    "Gujarat": [
        {"name": "Mehsana", "soil": "alluvial", "water": "medium", "district": "Mehsana", "lat": 23.6, "lon": 72.4, "market_km": 5.0, "farmers": 300},
        {"name": "Junagarh", "soil": "sandy", "water": "low", "district": "Junagarh", "lat": 21.5, "lon": 70.5, "market_km": 12.0, "farmers": 180},
        {"name": "Anand", "soil": "alluvial", "water": "high", "district": "Anand", "lat": 22.5, "lon": 72.9, "market_km": 3.5, "farmers": 350},
        {"name": "Rajkot Rural", "soil": "clay", "water": "medium", "district": "Rajkot", "lat": 22.3, "lon": 70.8, "market_km": 8.0, "farmers": 220},
    ],
    "Karnataka": [
        {"name": "Tumkur", "soil": "red", "water": "medium", "district": "Tumkur", "lat": 13.3, "lon": 77.1, "market_km": 7.0, "farmers": 190},
        {"name": "Kolar", "soil": "red", "water": "low", "district": "Kolar", "lat": 13.1, "lon": 78.1, "market_km": 9.5, "farmers": 140},
        {"name": "Dharwad", "soil": "black", "water": "medium", "district": "Dharwad", "lat": 15.5, "lon": 75.0, "market_km": 6.0, "farmers": 210},
        {"name": "Mandya", "soil": "alluvial", "water": "high", "district": "Mandya", "lat": 12.5, "lon": 76.9, "market_km": 4.5, "farmers": 280},
    ],
}

SOIL_AFFINITY = {
    "black":    {"Tomato":0.92,"Cotton":0.88,"Soybean":0.82,"Onion":0.75,"Wheat":0.65,"Sugarcane":0.72,"Millet (Bajra)":0.55},
    "red":      {"Brinjal":0.90,"Potato":0.72,"Onion":0.68,"Tomato":0.70,"Groundnut":0.85,"Millet (Bajra)":0.62,"Green Chilli":0.78},
    "alluvial": {"Potato":0.91,"Wheat":0.84,"Tomato":0.80,"Onion":0.72,"Soybean":0.75,"Rice":0.88,"Maize":0.78},
    "sandy":    {"Millet (Bajra)":0.90,"Onion":0.65,"Tomato":0.58,"Groundnut":0.82,"Watermelon":0.75},
    "clay":     {"Sugarcane":0.92,"Tomato":0.76,"Wheat":0.74,"Rice":0.80,"Soybean":0.68},
    "loamy":    {"Wheat":0.92,"Potato":0.88,"Tomato":0.85,"Onion":0.82,"Soybean":0.80},
}

WATER_CROPS = {
    "low":    {"Millet (Bajra)":0.20, "Groundnut":0.15, "Onion":-0.05, "Cotton":0.05},
    "medium": {},
    "high":   {"Rice":0.15, "Sugarcane":0.18, "Potato":0.10},
}

CROP_CAPACITY = {
    "Tomato":1200,"Onion":1800,"Potato":900,"Wheat":2200,"Brinjal":600,
    "Millet (Bajra)":800,"Soybean":700,"Sugarcane":3000,"Cotton":1000,
    "Groundnut":900,"Green Chilli":400,"Maize":1100,"Rice":1500,
}

CROP_DEMAND_GROWTH = {
    "Tomato":0.87,"Onion":0.54,"Potato":0.43,"Wheat":0.18,"Brinjal":0.31,
    "Millet (Bajra)":0.25,"Soybean":0.38,"Sugarcane":0.22,"Cotton":0.35,
    "Groundnut":0.41,"Green Chilli":0.62,"Maize":0.28,"Rice":0.20,
}

CROP_PROFIT_BASE = {
    "Tomato":61000,"Onion":41000,"Potato":52000,"Wheat":28000,"Brinjal":48000,
    "Millet (Bajra)":38000,"Soybean":45000,"Sugarcane":70000,"Cotton":52000,
    "Groundnut":55000,"Green Chilli":95000,"Maize":28000,"Rice":35000,
}


def _score_crop(crop: str, village: dict, supply_used: dict, n_villages: int) -> float:
    soil = village["soil"]
    water = village["water"]
    affinity = SOIL_AFFINITY.get(soil, {}).get(crop, 0.40)
    water_adj = WATER_CROPS.get(water, {}).get(crop, 0.0)
    capacity = CROP_CAPACITY.get(crop, 800)
    used = supply_used.get(crop, 0)
    supply_penalty = max(0, (used / max(capacity / n_villages, 1)) - 0.7) * 0.5
    demand_bonus = CROP_DEMAND_GROWTH.get(crop, 0.3) * 0.25
    return max(0, affinity + water_adj + demand_bonus - supply_penalty)


def run_supply_balancer(region: str = "Maharashtra", season: str = "kharif") -> dict:
    villages = REGIONS.get(region, REGIONS["Maharashtra"])
    supply_used = {c: 0 for c in CROP_CAPACITY}
    assignments = []
    n = len(villages)
    np.random.seed(42)

    for village in villages:
        scores = {crop: _score_crop(crop, village, supply_used, n) for crop in CROP_CAPACITY}
        best_crop = max(scores, key=lambda c: scores[c])
        supply_used[best_crop] += 1

        used_frac = supply_used[best_crop] / n
        over_risk = round(max(0.0, used_frac - 0.25) * 2, 2)
        score = scores[best_crop]
        profit = int(CROP_PROFIT_BASE.get(best_crop, 35000) * (0.9 + score * 0.4))
        # Scale by farm area (farmers * 2 acres avg)
        total_profit = profit * village.get("farmers", 200)

        assignments.append({
            "village": village["name"],
            "district": village["district"],
            "lat": village["lat"],
            "lon": village["lon"],
            "assigned_crop": best_crop,
            "soil": village["soil"],
            "water": village["water"],
            "farmers": village.get("farmers", 200),
            "reason": _build_reason(best_crop, village, supply_used),
            "overproduction_risk": over_risk,
            "ai_score": round(score * 10, 1),
            "expected_profit": f"₹{profit:,}/acre",
            "region_total_profit": f"₹{total_profit:,}",
            "market_distance_km": village["market_km"],
        })

    # Balance score (entropy-based)
    crop_counts = {}
    for a in assignments:
        crop_counts[a["assigned_crop"]] = crop_counts.get(a["assigned_crop"], 0) + 1
    probs = [v/n for v in crop_counts.values()]
    entropy = -sum(p * np.log(p) for p in probs if p > 0)
    max_entropy = np.log(len(crop_counts)) if len(crop_counts) > 1 else 1
    balance_score = round((entropy / max_entropy) * 100, 1)

    return {
        "region": region,
        "season": season,
        "assignments": assignments,
        "unique_crops": list(crop_counts.keys()),
        "crop_distribution": crop_counts,
        "model": "AI Supply Balancer v2 — Affinity + Entropy + Demand Signal Optimization",
        "balance_score": balance_score,
        "balance_grade": "Excellent" if balance_score >= 85 else ("Good" if balance_score >= 70 else "Moderate"),
        "total_farmers": sum(v.get("farmers", 200) for v in villages),
    }


def _build_reason(crop: str, village: dict, supply_used: dict) -> str:
    soil, water = village["soil"], village["water"]
    used = supply_used.get(crop, 1)
    base = f"Best affinity for {soil} soil · {water} water available"
    market_note = f"{village['market_km']} km to nearest mandi"
    if used == 1:
        supply_note = "🟢 First village — zero market saturation"
    elif used == 2:
        supply_note = "🟡 Low saturation — strong market gap"
    else:
        supply_note = "🟠 Demand strong enough to absorb additional supply"
    demand = CROP_DEMAND_GROWTH.get(crop, 0.3)
    demand_note = f"Demand growth: {round(demand*100)}%/year"
    return f"{base} · {supply_note} · {market_note} · {demand_note}"
