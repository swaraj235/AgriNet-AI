"""
AgriNet AI — Translation Routes
Real machine translation via LibreTranslate + hardcoded fallback.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/translate", tags=["translate"])

# ── Full translation strings (fallback) ───────────────────────────────────────
TRANSLATIONS = {
    "en": {
        "app_title": "AgriNet AI", "app_tagline": "Smart crop & supply network",
        "nav_dashboard": "Dashboard", "nav_crop": "Crop AI",
        "nav_transport": "Transport Pool", "nav_spoilage": "Spoilage AI",
        "nav_blockchain": "Blockchain", "nav_voice": "AI Advisor",
        "nav_market": "Market Prices", "nav_location": "My Farm",
        "demand_signal": "Demand signal", "farmers_connected": "Farmers connected",
        "profit_increase": "Avg profit increase", "spoilage_prevented": "Spoilage prevented",
        "forecast": "Live demand forecast — next 30 days",
        "forecast_sub": "Sources: real mandi API · OpenWeatherMap · festival demand signals",
        "supply_map": "AI Supply balance — region", "supply_sub": "AI prevents overproduction",
        "crop_ai_title": "Crop recommendation AI", "farmer_profile": "Farmer profile",
        "soil_type": "Soil type", "water_avail": "Water availability",
        "land_acres": "Land (acres)", "run_ai_btn": "Run AI recommendation",
        "validation_error": "Please select all parameters before running the AI.",
        "pool_title": "Farmers in your area", "pool_sub": "Click to add to transport pool",
        "calc_pool_btn": "Calculate shared transport",
        "pool_error": "Please select at least one farmer.",
        "spoilage_title": "Spoilage risk prediction",
        "spoilage_sub": "Shipments en route — AI monitors temperature & humidity",
        "chat_placeholder": "Ask anything about farming…",
        "login_title": "Welcome to AgriNet AI",
        "login_subtitle": "Smart farming intelligence for Indian farmers",
        "login_tab": "Login", "signup_tab": "Create Account",
        "email_label": "Email address", "password_label": "Password",
        "name_label": "Full name", "phone_label": "Phone (optional)",
        "login_btn": "Sign In", "signup_btn": "Create Account",
        "logout": "Logout", "welcome_back": "Welcome back",
        "weather_label": "Current weather", "location_label": "Your location",
        "mandi_prices": "Live mandi prices", "refresh": "Refresh",
        "crop_recommend": "Best crops for you", "market_signal": "Market signal",
        "ai_advisor": "AI Farm Advisor",
    },
    "hi": {
        "app_title": "एग्रीनेट एआई", "app_tagline": "स्मार्ट फसल और आपूर्ति नेटवर्क",
        "nav_dashboard": "डैशबोर्ड", "nav_crop": "फसल एआई",
        "nav_transport": "परिवहन पूल", "nav_spoilage": "खराबी एआई",
        "nav_blockchain": "ब्लॉकचेन", "nav_voice": "एआई सलाहकार",
        "nav_market": "बाज़ार भाव", "nav_location": "मेरा खेत",
        "demand_signal": "मांग संकेत", "farmers_connected": "जुड़े किसान",
        "profit_increase": "औसत लाभ वृद्धि", "spoilage_prevented": "खराबी रोकी",
        "forecast": "लाइव मांग पूर्वानुमान — अगले 30 दिन",
        "forecast_sub": "स्रोत: असली मंडी एपीआई · मौसम एपीआई · त्योहार संकेत",
        "supply_map": "एआई आपूर्ति संतुलन", "supply_sub": "एआई अतिउत्पादन रोकता है",
        "crop_ai_title": "फसल सिफारिश एआई", "farmer_profile": "किसान प्रोफ़ाइल",
        "soil_type": "मिट्टी का प्रकार", "water_avail": "पानी की उपलब्धता",
        "land_acres": "जमीन (एकड़)", "run_ai_btn": "एआई सिफारिश चलाएं",
        "validation_error": "एआई चलाने से पहले सभी पैरामीटर चुनें।",
        "pool_title": "आपके क्षेत्र में किसान", "pool_sub": "पूल में जोड़ने के लिए क्लिक करें",
        "calc_pool_btn": "साझा परिवहन गणना करें",
        "pool_error": "कम से कम एक किसान चुनें।",
        "spoilage_title": "खराबी जोखिम भविष्यवाणी",
        "spoilage_sub": "रास्ते में शिपमेंट — एआई निगरानी करता है",
        "chat_placeholder": "कोई भी कृषि प्रश्न पूछें…",
        "login_title": "एग्रीनेट एआई में आपका स्वागत है",
        "login_subtitle": "भारतीय किसानों के लिए स्मार्ट खेती",
        "login_tab": "लॉगिन", "signup_tab": "खाता बनाएं",
        "email_label": "ईमेल पता", "password_label": "पासवर्ड",
        "name_label": "पूरा नाम", "phone_label": "फोन (वैकल्पिक)",
        "login_btn": "साइन इन करें", "signup_btn": "खाता बनाएं",
        "logout": "लॉगआउट", "welcome_back": "वापस स्वागत है",
        "weather_label": "मौजूदा मौसम", "location_label": "आपका स्थान",
        "mandi_prices": "लाइव मंडी भाव", "refresh": "ताज़ा करें",
        "crop_recommend": "आपके लिए सर्वश्रेष्ठ फसलें", "market_signal": "बाज़ार संकेत",
        "ai_advisor": "एआई खेती सलाहकार",
    },
    "mr": {
        "app_title": "अॅग्रीनेट एआय", "app_tagline": "स्मार्ट पीक आणि पुरवठा नेटवर्क",
        "nav_dashboard": "डॅशबोर्ड", "nav_crop": "पीक एआय",
        "nav_transport": "वाहतूक पूल", "nav_spoilage": "नासाडी एआय",
        "nav_blockchain": "ब्लॉकचेन", "nav_voice": "एआय सल्लागार",
        "nav_market": "बाजारभाव", "nav_location": "माझं शेत",
        "demand_signal": "मागणी संकेत", "farmers_connected": "जोडलेले शेतकरी",
        "profit_increase": "सरासरी नफा वाढ", "spoilage_prevented": "नासाडी रोखली",
        "forecast": "थेट मागणी अंदाज — पुढील 30 दिवस",
        "forecast_sub": "स्रोत: खरे मंडी एपीआय · हवामान एपीआय · सण संकेत",
        "supply_map": "एआय पुरवठा संतुलन", "supply_sub": "एआय अतिउत्पादन टाळते",
        "crop_ai_title": "पीक शिफारस एआय", "farmer_profile": "शेतकरी प्रोफाइल",
        "soil_type": "मातीचा प्रकार", "water_avail": "पाण्याची उपलब्धता",
        "land_acres": "जमीन (एकर)", "run_ai_btn": "एआय शिफारस चालवा",
        "validation_error": "एआय चालवण्यापूर्वी सर्व मापदंड निवडा.",
        "pool_title": "तुमच्या भागातील शेतकरी", "pool_sub": "पूलमध्ये जोडण्यासाठी क्लिक करा",
        "calc_pool_btn": "सामायिक वाहतूक गणना करा",
        "pool_error": "किमान एक शेतकरी निवडा.",
        "spoilage_title": "नासाडी धोका अंदाज",
        "spoilage_sub": "मार्गावरील शिपमेंट — एआय लक्ष ठेवतो",
        "chat_placeholder": "शेतीबद्दल काहीही विचारा…",
        "login_title": "अॅग्रीनेट एआयमध्ये आपले स्वागत",
        "login_subtitle": "भारतीय शेतकऱ्यांसाठी स्मार्ट शेती",
        "login_tab": "लॉगिन", "signup_tab": "खाते तयार करा",
        "email_label": "ईमेल पत्ता", "password_label": "पासवर्ड",
        "name_label": "पूर्ण नाव", "phone_label": "फोन (पर्यायी)",
        "login_btn": "साइन इन करा", "signup_btn": "खाते तयार करा",
        "logout": "लॉगआउट", "welcome_back": "परत स्वागत",
        "weather_label": "सध्याचे हवामान", "location_label": "तुमचे स्थान",
        "mandi_prices": "थेट मंडी भाव", "refresh": "रिफ्रेश करा",
        "crop_recommend": "तुमच्यासाठी सर्वोत्तम पिके", "market_signal": "बाज़ार संकेत",
        "ai_advisor": "एआय शेती सल्लागार",
    },
}

LANG_CODES = {"en": "en", "hi": "hi", "mr": "mr"}


class TranslateRequest(BaseModel):
    text: str
    target: str = "en"
    source: str = "auto"


async def _libretranslate(text: str, source: str, target: str) -> str:
    """Call LibreTranslate API."""
    payload = {"q": text, "source": source, "target": target, "format": "text"}
    if settings.libre_translate_key:
        payload["api_key"] = settings.libre_translate_key

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{settings.libre_translate_url}/translate", json=payload)
        r.raise_for_status()
        return r.json().get("translatedText", text)


@router.post("")
async def translate(body: TranslateRequest):
    """Translate arbitrary text to a target language."""
    if body.target not in ("en", "hi", "mr", "ta", "te", "kn", "gu", "pa", "bn"):
        raise HTTPException(400, "Unsupported target language")

    if len(body.text) > 2000:
        raise HTTPException(400, "Text too long (max 2000 chars)")

    try:
        translated = await _libretranslate(body.text, body.source, body.target)
        return {"translated": translated, "source": body.source, "target": body.target, "engine": "libretranslate"}
    except Exception as e:
        print(f"[LibreTranslate] Error: {e}")
        return {"translated": body.text, "source": body.source, "target": body.target, "engine": "passthrough", "error": str(e)}


@router.get("/strings/{lang}")
async def get_strings(lang: str):
    """Return all UI translation strings for a given language."""
    lang = lang[:5]
    strings = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return strings


@router.get("/languages")
async def get_languages():
    """Return supported languages."""
    return {
        "languages": [
            {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
            {"code": "hi", "name": "Hindi", "native": "हिंदी", "flag": "🇮🇳"},
            {"code": "mr", "name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
            {"code": "ta", "name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
            {"code": "te", "name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
            {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳"},
            {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
        ]
    }
