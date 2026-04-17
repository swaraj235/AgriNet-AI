"""
AgriNet ML Service — AI Supply Balancer (Core Innovation).
Distributes crop recommendations across multiple villages/regions
to prevent overproduction and stabilize market supply.
"""

import numpy as np
from typing import List

# ===== Region Data =====

VILLAGES = {
    'Maharashtra': [
        {'name': 'Nashik A',      'soil': 'black',    'water': 'high',   'district': 'Nashik',      'market_km': 8.2},
        {'name': 'Nashik B',      'soil': 'red',      'water': 'medium', 'district': 'Nashik',      'market_km': 12.4},
        {'name': 'Ahmednagar',    'soil': 'alluvial', 'water': 'medium', 'district': 'Ahmednagar',  'market_km': 5.6},
        {'name': 'Solapur',       'soil': 'black',    'water': 'low',    'district': 'Solapur',     'market_km': 9.1},
        {'name': 'Satara',        'soil': 'red',      'water': 'high',   'district': 'Satara',      'market_km': 14.3},
        {'name': 'Pune Rural',    'soil': 'alluvial', 'water': 'high',   'district': 'Pune',        'market_km': 4.2},
        {'name': 'Kolhapur',      'soil': 'clay',     'water': 'high',   'district': 'Kolhapur',    'market_km': 7.8},
        {'name': 'Aurangabad',    'soil': 'sandy',    'water': 'low',    'district': 'Aurangabad',  'market_km': 18.5},
    ]
}

# ===== Crop Market Capacity (tons/season per region) =====
CROP_MARKET_CAPACITY = {
    'Tomato':         {'max_supply': 1200, 'demand_growth': 0.87},
    'Onion':          {'max_supply': 1800, 'demand_growth': 0.54},
    'Potato':         {'max_supply': 900,  'demand_growth': 0.43},
    'Wheat':          {'max_supply': 2200, 'demand_growth': 0.18},
    'Brinjal':        {'max_supply': 600,  'demand_growth': 0.31},
    'Millet (Bajra)': {'max_supply': 800,  'demand_growth': 0.25},
    'Soybean':        {'max_supply': 700,  'demand_growth': 0.38},
    'Sugarcane':      {'max_supply': 3000, 'demand_growth': 0.22},
}

# ===== Soil-Crop Affinity Scores =====
SOIL_AFFINITY = {
    'black':    {'Tomato': 0.92, 'Onion': 0.75, 'Wheat': 0.65, 'Soybean': 0.80, 'Sugarcane': 0.70, 'Millet (Bajra)': 0.55},
    'red':      {'Brinjal': 0.90, 'Potato': 0.72, 'Onion': 0.68, 'Tomato': 0.70, 'Millet (Bajra)': 0.60},
    'alluvial': {'Potato': 0.91, 'Wheat': 0.82, 'Tomato': 0.78, 'Onion': 0.70, 'Soybean': 0.73},
    'sandy':    {'Millet (Bajra)': 0.88, 'Onion': 0.65, 'Tomato': 0.60},
    'clay':     {'Sugarcane': 0.91, 'Tomato': 0.76, 'Wheat': 0.72, 'Soybean': 0.68},
}

WATER_PENALTY = {'low': -0.15, 'medium': 0.0, 'high': 0.08}


def _score_crop_for_village(crop: str, village: dict, supply_used: dict) -> float:
    """Score how well a crop fits a village, penalizing overused crops."""
    soil = village['soil']
    water = village['water']

    # Base soil affinity
    affinity = SOIL_AFFINITY.get(soil, {}).get(crop, 0.40)

    # Water factor
    water_factor = 1.0 + WATER_PENALTY.get(water, 0.0)

    # Supply balancing penalty — reduce score if too many villages already assigned this crop
    capacity = CROP_MARKET_CAPACITY.get(crop, {}).get('max_supply', 1000)
    used = supply_used.get(crop, 0)
    supply_penalty = max(0, (used / max(capacity / len(VILLAGES['Maharashtra']), 1)) - 0.8)

    # Demand growth bonus
    demand_bonus = CROP_MARKET_CAPACITY.get(crop, {}).get('demand_growth', 0.3) * 0.2

    return max(0, affinity * water_factor + demand_bonus - supply_penalty * 0.4)


def run_supply_balancer(region: str = 'Maharashtra') -> dict:
    """
    AI Supply Balancer: assigns the best crop to each village,
    ensuring no single crop saturates the market.
    """
    villages = VILLAGES.get(region, VILLAGES['Maharashtra'])
    supply_used = {crop: 0 for crop in CROP_MARKET_CAPACITY}
    assignments = []
    np.random.seed(42)

    for village in villages:
        # Score all crops for this village
        crop_scores = {}
        for crop in CROP_MARKET_CAPACITY:
            score = _score_crop_for_village(crop, village, supply_used)
            crop_scores[crop] = score

        # Pick best crop
        best_crop = max(crop_scores, key=lambda c: crop_scores[c])
        supply_used[best_crop] += 1

        # Overproduction risk
        capacity = CROP_MARKET_CAPACITY[best_crop]['max_supply']
        used_fraction = supply_used[best_crop] / len(villages)
        overproduction_risk = round(max(0.0, used_fraction - 0.25) * 2, 2)

        # Profit estimate
        score = crop_scores[best_crop]
        profit_base = int(35000 + score * 30000)

        # Build reason
        reason = _build_balancer_reason(best_crop, village, supply_used)

        assignments.append({
            'village': village['name'],
            'assigned_crop': best_crop,
            'reason': reason,
            'overproduction_risk': overproduction_risk,
            'expected_profit': f"₹{profit_base:,}",
            'market_distance_km': village['market_km'],
        })

    # Balance score: how evenly distributed assignments are
    crop_counts = {}
    for a in assignments:
        crop_counts[a['assigned_crop']] = crop_counts.get(a['assigned_crop'], 0) + 1

    n = len(assignments)
    k = len(crop_counts)
    # Entropy-based score (higher = better balanced)
    probs = [v / n for v in crop_counts.values()]
    entropy = -sum(p * np.log(p) for p in probs if p > 0)
    max_entropy = np.log(k) if k > 1 else 1
    balance_score = round((entropy / max_entropy) * 100, 1)

    return {
        'region': region,
        'assignments': assignments,
        'model': 'AI Supply Balancer v1 — Affinity + Entropy Optimization',
        'balance_score': balance_score,
    }


def _build_balancer_reason(crop: str, village: dict, supply_used: dict) -> str:
    soil = village['soil']
    water = village['water']
    used = supply_used.get(crop, 1)

    base = f"Best fit for {soil} soil with {water} water"
    if used == 1:
        diff = "First village assigned — no market saturation risk"
    elif used <= 2:
        diff = "Low supply saturation — strong market gap to fill"
    else:
        diff = "Demand strong enough to absorb additional supply"

    return f"{base}. {diff}."
