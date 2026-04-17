"""
AgriNet ML Service — Random Forest Crop Recommendation Model.
Uses sklearn for a realistic demo with simulated training data.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# ===== Feature Engineering =====

SOIL_TYPES = ['black', 'red', 'alluvial', 'sandy', 'clay']
WATER_LEVELS = ['low', 'medium', 'high']
LAND_SIZES = ['small', 'medium', 'large']
SEASONS = ['kharif', 'rabi', 'zaid']
CROPS = ['Tomato', 'Onion', 'Potato', 'Wheat', 'Brinjal', 'Millet (Bajra)', 'Soybean', 'Sugarcane']

# Encode mappings
SOIL_MAP = {s: i for i, s in enumerate(SOIL_TYPES)}
WATER_MAP = {w: i for i, w in enumerate(WATER_LEVELS)}
LAND_MAP = {l: i for i, l in enumerate(LAND_SIZES)}
SEASON_MAP = {s: i for i, s in enumerate(SEASONS)}
CROP_MAP = {c: i for i, c in enumerate(CROPS)}
CROP_INV = {i: c for c, i in CROP_MAP.items()}

# ===== Simulated Training Data =====

# Features: [soil_idx, water_idx, land_idx, season_idx]
# Labels: crop_idx
_TRAINING_DATA = [
    # Black soil crops
    ([0, 2, 2, 0], 0),  # black, high water, large → Tomato
    ([0, 2, 1, 0], 0),  # black, high water, medium → Tomato
    ([0, 1, 1, 1], 1),  # black, medium water, medium, rabi → Onion
    ([0, 1, 0, 1], 1),  # black, medium, small, rabi → Onion
    ([0, 2, 2, 1], 2),  # black, high, large, rabi → Wheat
    ([0, 0, 0, 0], 5),  # black, low, small → Millet
    ([0, 2, 2, 2], 7),  # black, high, large, zaid → Sugarcane
    ([0, 1, 1, 0], 6),  # black, medium, medium, kharif → Soybean

    # Red soil crops
    ([1, 2, 1, 0], 4),  # red, high, medium → Brinjal
    ([1, 2, 2, 0], 4),  # red, high, large → Brinjal
    ([1, 1, 0, 0], 4),  # red, medium, small → Brinjal
    ([1, 1, 1, 1], 1),  # red, medium, medium, rabi → Onion
    ([1, 0, 0, 0], 5),  # red, low → Millet
    ([1, 2, 2, 1], 2),  # red, high, large, rabi → Potato

    # Alluvial soil crops
    ([2, 2, 2, 1], 2),  # alluvial, high, large, rabi → Potato
    ([2, 2, 1, 1], 2),  # alluvial, high, medium, rabi → Potato
    ([2, 2, 2, 1], 3),  # alluvial, high, large, rabi → Wheat
    ([2, 1, 1, 0], 0),  # alluvial, medium, medium, kharif → Tomato
    ([2, 2, 2, 0], 6),  # alluvial, high, large, kharif → Soybean
    ([2, 1, 0, 2], 1),  # alluvial, medium, small, zaid → Onion

    # Sandy soil crops
    ([3, 0, 0, 0], 5),  # sandy, low → Millet
    ([3, 0, 1, 0], 5),  # sandy, low, medium → Millet
    ([3, 1, 1, 1], 1),  # sandy, medium, medium, rabi → Onion
    ([3, 2, 2, 0], 0),  # sandy, high, large → Tomato

    # Clay soil crops
    ([4, 2, 2, 0], 7),  # clay, high → Sugarcane
    ([4, 2, 1, 0], 0),  # clay, high, medium → Tomato
    ([4, 1, 1, 1], 3),  # clay, medium, medium, rabi → Wheat
    ([4, 0, 0, 0], 5),  # clay, low → Millet
]

# Augment with slight noise for realism
def _build_training_set():
    X, y = [], []
    for features, label in _TRAINING_DATA:
        X.append(features)
        y.append(label)
        # Add 3 augmented copies with small feature perturbations
        for _ in range(3):
            noisy = [min(max(0, f + np.random.randint(-1, 2)), [4, 2, 2, 3][i])
                     for i, f in enumerate(features)]
            X.append(noisy)
            y.append(label)
    return np.array(X), np.array(y)


# ===== Model Training =====

class CropRecommendationModel:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            class_weight='balanced'
        )
        self._train()

    def _train(self):
        X, y = _build_training_set()
        self.model.fit(X, y)

    def _encode(self, soil, water, land, season='kharif'):
        return [
            SOIL_MAP.get(soil, 0),
            WATER_MAP.get(water, 1),
            LAND_MAP.get(land, 1),
            SEASON_MAP.get(season, 0)
        ]

    def predict(self, soil, water, land, season='kharif'):
        features = np.array([self._encode(soil, water, land, season)])
        proba = self.model.predict_proba(features)[0]

        # Build ranked results
        results = []
        for crop_idx, prob in enumerate(proba):
            if prob < 0.02:
                continue
            crop = CROP_INV.get(crop_idx, 'Unknown')
            score = round(prob * 10, 1)

            # Feature importance (simulated per-crop)
            fi = self.model.feature_importances_
            results.append({
                'crop': crop,
                'score': min(score, 9.9),
                'match': 'Excellent' if prob > 0.25 else ('Good' if prob > 0.12 else 'Average'),
                'profit': _estimate_profit(crop, land),
                'reason': _build_reason(crop, soil, water, land),
                'confidence': round(prob * 100, 1),
                'feature_importance': {
                    'soil': round(float(fi[0]), 3),
                    'water': round(float(fi[1]), 3),
                    'land_size': round(float(fi[2]), 3),
                    'season': round(float(fi[3]), 3)
                }
            })

        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:4] or _fallback(soil, water, land)


# ===== Profit Estimation =====

PROFIT_BASE = {
    'Tomato': 61000, 'Onion': 41000, 'Potato': 52000, 'Wheat': 28000,
    'Brinjal': 48000, 'Millet (Bajra)': 38000, 'Soybean': 45000, 'Sugarcane': 70000
}
LAND_MULTIPLIER = {'small': 0.7, 'medium': 1.0, 'large': 1.4}

def _estimate_profit(crop, land):
    base = PROFIT_BASE.get(crop, 35000)
    mult = LAND_MULTIPLIER.get(land, 1.0)
    val = int(base * mult)
    return f"₹{val:,}"


def _build_reason(crop, soil, water, land):
    reasons = {
        'Tomato': f"High demand in Pune mandi · {soil} soil with {water} irrigation suits tomato",
        'Onion': f"Stable mandi prices · {soil} soil with {water} water is ideal for onion",
        'Potato': f"Best yield in {soil} soil · Cold storage nearby for post-harvest",
        'Wheat': f"Consistent local demand · {water} water availability is sufficient",
        'Brinjal': f"Export demand rising · thrives in {soil} laterite conditions",
        'Millet (Bajra)': f"Highly drought resistant · ideal for {water} rainfed conditions",
        'Soybean': f"High market demand · suits {soil} soil with adequate rainfall",
        'Sugarcane': f"High sugar mills demand · {land} land with {water} water maximizes yield"
    }
    return reasons.get(crop, f"Suitable match for {soil} soil and {water} water conditions")


def _fallback(soil, water, land):
    return [{
        'crop': 'Onion',
        'score': 7.2,
        'match': 'Good',
        'profit': _estimate_profit('Onion', land),
        'reason': _build_reason('Onion', soil, water, land),
        'confidence': 72.0,
        'feature_importance': {'soil': 0.42, 'water': 0.28, 'land_size': 0.18, 'season': 0.12}
    }]


# Singleton
_crop_model = None

def get_crop_model():
    global _crop_model
    if _crop_model is None:
        _crop_model = CropRecommendationModel()
    return _crop_model
