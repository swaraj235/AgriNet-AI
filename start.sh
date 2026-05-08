#!/bin/bash
# ============================================
# AgriNet AI v2.0 — Start Script
# Single FastAPI server on port 8000
# ============================================

ROOT="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GREEN}  🌱 AgriNet AI v2.0 — Starting${NC}"
echo "  ======================================="

# Check for .env file
if [ ! -f "$ROOT/.env" ]; then
    echo -e "${YELLOW}  ⚠️  No .env file found. Copying from .env.example...${NC}"
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo -e "${YELLOW}  📝 Edit .env to add your API keys for full functionality${NC}"
fi

# Kill previous instances
pkill -f "uvicorn.*backend.main" 2>/dev/null
pkill -f "python.*server.py" 2>/dev/null
pkill -f "uvicorn.*ml_service" 2>/dev/null
sleep 1

# Use existing venv if available, else try system python
if [ -f "$ROOT/venv/bin/python" ]; then
    PYTHON="$ROOT/venv/bin/python"
    PIP="$ROOT/venv/bin/pip"
elif [ -f "$ROOT/ml_venv/bin/python" ]; then
    PYTHON="$ROOT/ml_venv/bin/python"
    PIP="$ROOT/ml_venv/bin/pip"
else
    PYTHON="python3"
    PIP="pip3"
fi

echo -e "${YELLOW}  📦 Using Python: $(${PYTHON} --version 2>&1)${NC}"

# Install/upgrade dependencies
echo -e "${YELLOW}  📦 Installing dependencies...${NC}"
${PIP} install -q -r "$ROOT/requirements.txt"

# Create frontend directory if needed
mkdir -p "$ROOT/frontend/css" "$ROOT/frontend/js"

# Start FastAPI server
echo -e "${YELLOW}  🚀 Starting AgriNet AI FastAPI server on port 8000...${NC}"
cd "$ROOT"
${PYTHON} -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!
echo "     PID: $SERVER_PID"

sleep 3

# Check if server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    echo ""
    echo -e "${GREEN}  ✅ AgriNet AI v2.0 is running!${NC}"
    echo "  ───────────────────────────────────────"
    echo "  🌐 App          → http://localhost:8000"
    echo "  📖 API Docs     → http://localhost:8000/docs"
    echo "  ❤️  Health       → http://localhost:8000/health"
    echo "  📡 Market API   → http://localhost:8000/api/market/prices"
    echo "  🤖 Crop AI      → http://localhost:8000/api/ml/crop-recommend"
    echo "  🌤️  Weather      → http://localhost:8000/api/weather/current"
    echo "  ───────────────────────────────────────"
    echo -e "  ${YELLOW}Add API keys to .env for full functionality${NC}"
    echo "  Press Ctrl+C to stop"
    echo ""
else
    echo -e "${RED}  ❌ Server failed to start. Check logs above.${NC}"
    exit 1
fi

trap "kill $SERVER_PID 2>/dev/null; echo '  ⛔ AgriNet AI stopped.'; exit 0" SIGINT SIGTERM
wait $SERVER_PID
