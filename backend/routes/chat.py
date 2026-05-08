"""
AgriNet AI — Intelligent Chatbot Route
Uses OpenRouter LLM (Mistral-7B free) with full farming context injection.
Gracefully falls back to rule-based responses if no API key.
"""

import json
import re
from typing import Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.config import get_settings
from backend.auth import get_optional_user

settings = get_settings()
router = APIRouter(prefix="/api/chat", tags=["chat"])

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are AgriNet AI — an expert agricultural advisor for Indian farmers.
You speak in a warm, simple, and practical tone. You understand Hindi, Marathi, Tamil, Telugu, Kannada, and English.
Always respond in the SAME language the user wrote in.

Your expertise:
- Crop selection based on soil type, season, water availability
- Mandi prices and when to sell for maximum profit
- Transport pooling to reduce costs
- Spoilage prevention and cold storage advice
- Weather-based farming decisions
- Government schemes: PM-KISAN, e-NAM, PMFBY, KCC (Kisan Credit Card)
- Organic farming, integrated pest management
- Post-harvest storage and value addition

CONTEXT (injected at runtime):
{context}

Rules:
1. Give specific, actionable advice — not generic statements  
2. Mention real money amounts in Indian Rupees (₹)
3. If asked about mandi prices or weather, use the context data provided
4. Be brief (2-4 sentences) unless the farmer asks for detail
5. Never make up scientific facts — say "I'm not sure" if uncertain
6. For diseases/pests, suggest both organic and chemical remedies
7. Always end with ONE follow-up question to understand the farmer better
"""

# ── Rule-based fallback ────────────────────────────────────────────────────────
FALLBACK_RESPONSES = {
    "en": {
        "tomato": "🍅 Tomatoes are in high demand right now. Based on typical Pune APMC rates, you can expect ₹18–25/kg. Harvest in the evening and transport early morning to maintain freshness. Which district are you in?",
        "onion": "🧅 Onion prices are volatile. Lasalgaon APMC in Nashik is usually the best market. Best to sell when prices cross ₹15/kg. Are you planning to store or sell immediately?",
        "weather": "🌦️ Check your local weather before spraying pesticides — avoid spraying within 24 hours of rain as it reduces effectiveness. What crop are you planning to spray?",
        "transport": "🚛 Transport pooling with 3-4 nearby farmers can cut your cost from ₹4,000 to under ₹1,200 per trip. Use the Transport Pool feature to find neighbors. How many acres are you transporting from?",
        "soil": "🌱 Get your soil tested at your nearest KVK (Krishi Vigyan Kendra) — it costs only ₹100-200 and tells you exact NPK levels. This helps choose the right fertilizer. Which crop are you planning?",
        "default": "👋 I'm AgriNet AI, your farming advisor! I can help with crop selection, mandi prices, weather advice, and transport pooling. What's your biggest farming challenge right now?",
    },
    "hi": {
        "default": "👋 नमस्ते! मैं एग्रीनेट एआई हूँ। मैं फसल चुनाव, मंडी भाव, मौसम सलाह और परिवहन में मदद कर सकता हूँ। आपकी सबसे बड़ी समस्या क्या है?",
        "tomato": "🍅 टमाटर की अभी अच्छी मांग है। पुणे APMC में ₹18–25/किलो मिल रहा है। शाम को तोड़ें और सुबह जल्दी भेजें — ताजगी बनी रहेगी। आप किस जिले में हैं?",
        "transport": "🚛 3-4 किसानों के साथ मिलकर गाड़ी करें — खर्च ₹4,000 से घटकर ₹1,200 हो जाता है। ट्रांसपोर्ट पूल सुविधा से पास के किसान खोजें। कितने एकड़ की फसल है?",
    },
    "mr": {
        "default": "👋 नमस्कार! मी अॅग्रीनेट एआय आहे. पीक निवड, मंडी भाव, हवामान सल्ला आणि वाहतुकीत मदत करतो. तुमची सर्वात मोठी शेती समस्या कोणती?",
        "tomato": "🍅 टोमॅटोला सध्या चांगली मागणी आहे. पुणे मंडीत ₹18–25/किलो मिळत आहे. संध्याकाळी काढा आणि सकाळी लवकर पाठवा. तुम्ही कोणत्या जिल्ह्यात आहात?",
    },
}

def _detect_language(text: str) -> str:
    """Simple language detection."""
    hi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    mr_chars = len(re.findall(r'[\u0900-\u097F]', text))
    if hi_chars > 3:
        # Distinguish Hindi vs Marathi by some common Marathi-specific words
        marathi_words = ["आहे", "कोणत्या", "पाठवा", "शेत", "काढा", "मंडी"]
        if any(w in text for w in marathi_words):
            return "mr"
        return "hi"
    return "en"


def _rule_based_response(text: str, lang: str, context: dict) -> str:
    """Fallback rule-based response when LLM not available."""
    text_lower = text.lower()
    responses = FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES["en"])

    # Keyword matching
    if any(w in text_lower for w in ["tomato", "tamatar", "tomatoes", "टमाटर", "टोमॅटो"]):
        return responses.get("tomato", responses["default"])
    if any(w in text_lower for w in ["onion", "pyaaz", "kanda", "प्याज", "कांदा"]):
        return responses.get("onion", responses["default"])
    if any(w in text_lower for w in ["weather", "mausam", "rain", "baarish", "मौसम", "पाऊस"]):
        # Add real weather if available
        if context.get("weather"):
            w = context["weather"]
            temp = w.get("temperature_c", "--")
            hum = w.get("humidity_pct", "--")
            desc = w.get("description", "")
            if lang == "hi":
                return f"🌡️ अभी {desc} है — तापमान {temp}°C, नमी {hum}%। {w.get('forecast_text', '')} कौन सी फसल पर स्प्रे करना है?"
            if lang == "mr":
                return f"🌡️ सध्या {desc} आहे — तापमान {temp}°C, आर्द्रता {hum}%। {w.get('forecast_text', '')} कोणत्या पिकावर फवारणी करायची?"
            return f"🌡️ Current weather: {desc}, {temp}°C, {hum}% humidity. {w.get('forecast_text', '')} What crop are you spraying?"
    if any(w in text_lower for w in ["transport", "truck", "gaadi", "ट्रक", "वाहन", "गाडी"]):
        return responses.get("transport", responses["default"])
    if any(w in text_lower for w in ["soil", "mitti", "माती", "मिट्टी"]):
        return responses.get("soil", responses["default"])

    # Price queries
    if any(w in text_lower for w in ["price", "bhav", "rate", "भाव", "दर", "किमत"]):
        crop_prices = context.get("mandi_prices", [])
        if crop_prices:
            price_list = ", ".join([f"{p['crop']}: ₹{p['price_per_kg']}/kg" for p in crop_prices[:4]])
            if lang == "hi":
                return f"📊 आज के मंडी भाव: {price_list}। कौन सी फसल बेचनी है?"
            return f"📊 Today's mandi rates: {price_list}. Which crop are you selling?"

    return responses["default"]


class ChatRequest(BaseModel):
    message: str
    history: list = []
    language: str = "auto"
    context: dict = {}


@router.post("/send")
async def send_chat(
    body: ChatRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """Send a message and get an AI response."""
    if not body.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if len(body.message) > 1000:
        raise HTTPException(400, "Message too long (max 1000 chars)")

    lang = body.language if body.language != "auto" else _detect_language(body.message)
    context = body.context

    # Try LLM
    if settings.has_llm:
        try:
            # Build context string
            ctx_parts = []
            if context.get("weather"):
                w = context["weather"]
                ctx_parts.append(f"Weather: {w.get('description','')}, {w.get('temperature_c','--')}°C, humidity {w.get('humidity_pct','--')}%")
            if context.get("location"):
                loc = context["location"]
                ctx_parts.append(f"Farmer location: {loc.get('village','')}, {loc.get('district','')}, {loc.get('state','')}")
            if context.get("mandi_prices"):
                prices = context["mandi_prices"][:4]
                price_str = ", ".join([f"{p['crop']} ₹{p['price_per_kg']}/kg" for p in prices])
                ctx_parts.append(f"Today's mandi prices: {price_str}")
            if current_user:
                ctx_parts.append(f"Farmer name: {current_user.get('name', 'Farmer')}")

            ctx_str = "\n".join(ctx_parts) if ctx_parts else "No live context available."

            # Build messages
            messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=ctx_str)}]
            for h in body.history[-6:]:  # Last 3 turns
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": body.message})

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "HTTP-Referer": "https://agrinet.ai",
                        "X-Title": "AgriNet AI",
                    },
                    json={
                        "model": settings.openrouter_model,
                        "messages": messages,
                        "max_tokens": 400,
                        "temperature": 0.7,
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data["choices"][0]["message"]["content"].strip()

                return {
                    "reply": reply,
                    "lang": lang,
                    "engine": "llm",
                    "model": settings.openrouter_model,
                }
        except Exception as e:
            print(f"[Chat/LLM] Error: {e}. Falling back to rule-based.")

    # Fallback
    reply = _rule_based_response(body.message, lang, context)
    return {
        "reply": reply,
        "lang": lang,
        "engine": "rule-based",
        "model": "agrinet-rules-v2",
    }
