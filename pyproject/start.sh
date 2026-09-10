#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Start FastAPI backend
cd "$ROOT/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Vite frontend (exposed preview port)
cd "$ROOT/frontend"
npm run dev

trap 'kill $BACKEND_PID' EXIT
