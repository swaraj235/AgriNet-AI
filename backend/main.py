"""
AgriNet AI — FastAPI Main Application
Single server replacing both Flask + old FastAPI ML service.
Serves static frontend + all API routes on port 8000.
"""

import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import get_settings
from backend.routes import auth, weather, location, translate, chat, market, ml

settings = get_settings()

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ── Lifespan (startup/shutdown) ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n  🌱 AgriNet AI — Starting up")
    print(f"  📊 Supabase: {'✅ Connected' if settings.has_supabase else '⚠️ SQLite fallback'}")
    print(f"  🌤️  Weather API: {'✅ OpenWeatherMap' if settings.has_weather_api else '⚠️ Simulated'}")
    print(f"  🗺️  Geocoding: {'✅ OpenCage' if settings.has_geocode_api else '⚠️ Estimated'}")
    print(f"  🤖 LLM Chat: {'✅ OpenRouter' if settings.has_llm else '⚠️ Rule-based'}")

    # Init SQLite if not using Supabase
    if not settings.has_supabase:
        from backend.db.supabase_client import init_sqlite
        init_sqlite()
        print("  🗄️  SQLite database initialized")

    # Pre-warm ML models in background
    try:
        from backend.ml.crop_model import get_crop_model
        from backend.ml.spoilage_model import get_spoilage_model
        model = get_crop_model()
        spoilage = get_spoilage_model()
        print(f"  🧬 ML Models: ✅ Crop ({len(model.crop_labels)} crops) + Spoilage loaded")
    except Exception as e:
        print(f"  🧬 ML Models: ⚠️ {e}")

    print(f"  🌐 API Docs: http://localhost:8000/docs")
    print(f"  🚀 App: http://localhost:8000\n")

    yield  # App is running

    # Shutdown
    print("\n  ⛔ AgriNet AI shutting down\n")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AgriNet AI",
    description="Smart farming intelligence platform for Indian farmers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security Headers Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Request Timing Middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{round((time.time() - start) * 1000)}ms"
    return response


# ── API Routes ────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(weather.router)
app.include_router(location.router)
app.include_router(translate.router)
app.include_router(chat.router)
app.include_router(market.router)
app.include_router(ml.router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "AgriNet AI v2.0",
        "supabase": settings.has_supabase,
        "weather_api": settings.has_weather_api,
        "geocoding": settings.has_geocode_api,
        "llm": settings.has_llm,
    }


# ── Static Files (Frontend) ───────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    # Serve CSS, JS etc.
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js",  StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")),  name="js")

    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

    @app.get("/app")
    @app.get("/index.html")
    async def serve_app():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/login")
    @app.get("/login.html")
    async def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

    # Catch-all for SPA
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # API routes are handled above; 404 for unknown paths
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        return JSONResponse({
            "message": "AgriNet AI API v2.0",
            "docs": "/docs",
            "health": "/health",
            "note": "Frontend not found — run from project root"
        })


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))],
    )
