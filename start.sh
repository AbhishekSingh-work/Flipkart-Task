#!/bin/bash
# ============================================================
#  Logistics Verification Hub - Single Script Launcher
#  Starts: Redis → Celery → FastAPI App
#  Usage:  bash start.sh
# ============================================================

set -e

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Configuration ──
VENV_DIR=".venv"
REDIS_PORT=6379
APP_HOST="127.0.0.1"
APP_PORT=8000

PIDS=()

# ── Cleanup on exit ──
cleanup() {
    echo ""
    echo -e "${CYAN}[INFO] Shutting down all services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo -e "${GREEN}[OK]   Stopped process $pid${NC}"
        fi
    done
    # Also kill any redis-server we spawned
    if [ -n "$REDIS_PID" ]; then
        kill "$REDIS_PID" 2>/dev/null && echo -e "${GREEN}[OK]   Redis stopped${NC}"
    fi
    echo -e "${GREEN}[OK]   All services stopped.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "============================================================"
echo "          LOGISTICS VERIFICATION HUB - LAUNCHER"
echo "============================================================"
echo ""

# ── Activate venv ──
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate" 2>/dev/null || source "$VENV_DIR/Scripts/activate" 2>/dev/null
    echo -e "${GREEN}[OK]   Virtual environment activated${NC}"
else
    echo -e "${RED}[ERROR] Virtual environment not found at $VENV_DIR${NC}"
    echo "        Run: python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# ── 1. Start Redis ──
echo -e "${CYAN}[1/3] Starting Redis Server...${NC}"
if command -v redis-server &>/dev/null; then
    redis-server --port $REDIS_PORT --daemonize no &
    REDIS_PID=$!
    PIDS+=($REDIS_PID)
    sleep 1
    echo -e "${GREEN}[OK]   Redis started on port $REDIS_PORT (PID: $REDIS_PID)${NC}"
else
    echo -e "${YELLOW}[WARN] redis-server not found. Tasks will run synchronously.${NC}"
    REDIS_PID=""
fi

# ── 2. Start Celery Worker ──
echo -e "${CYAN}[2/3] Starting Celery Worker...${NC}"
if [ -n "$REDIS_PID" ]; then
    celery -A app.celery_app worker --loglevel=info -P threads &
    CELERY_PID=$!
    PIDS+=($CELERY_PID)
    sleep 2
    echo -e "${GREEN}[OK]   Celery worker started (PID: $CELERY_PID)${NC}"
else
    echo -e "${YELLOW}[SKIP] Celery worker skipped (no Redis).${NC}"
fi

# ── 3. Start FastAPI App ──
echo -e "${CYAN}[3/3] Starting FastAPI App...${NC}"
echo ""
echo "============================================================"
echo -e "  ${GREEN}All services launched!${NC}"
echo "  App:    http://$APP_HOST:$APP_PORT"
echo "  Press Ctrl+C to stop all services."
echo "============================================================"
echo ""

python -m uvicorn app.main:app --host $APP_HOST --port $APP_PORT
