#!/bin/bash
# ============================================
# AgriNet AI — Start Script
# Launches both Flask (port 5000) and FastAPI ML (port 8000)
# ============================================

ROOT="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${GREEN}  🌱 AgriNet AI — Starting All Services${NC}"
echo "  ======================================="

# Kill any existing servers
pkill -f "python.*server.py" 2>/dev/null
pkill -f "uvicorn.*main" 2>/dev/null
sleep 1

# Start FastAPI ML service
echo -e "${YELLOW}  🤖 Starting FastAPI ML Service on port 8000...${NC}"
cd "$ROOT/ml_service"
"$ROOT/ml_venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
ML_PID=$!
echo "     PID: $ML_PID"

sleep 3

# Start Flask main app
echo -e "${YELLOW}  🌐 Starting Flask Web App on port 5000...${NC}"
cd "$ROOT"
source "$ROOT/venv/bin/activate"
python server.py &
FLASK_PID=$!
echo "     PID: $FLASK_PID"

sleep 2

echo ""
echo -e "${GREEN}  ✅ AgriNet AI is running!${NC}"
echo "  ───────────────────────────────────────"
echo "  🌐 Web App     → http://localhost:5000"
echo "  📱 Mobile UI   → http://localhost:5000/mobile"
echo "  🤖 ML Service  → http://localhost:8000"
echo "  📖 API Docs    → http://localhost:8000/docs"
echo "  ───────────────────────────────────────"
echo "  Press Ctrl+C to stop all services"
echo ""

# Wait and forward signals
trap "kill $ML_PID $FLASK_PID 2>/dev/null; echo '  ⛔ Services stopped.'; exit 0" SIGINT SIGTERM
wait
