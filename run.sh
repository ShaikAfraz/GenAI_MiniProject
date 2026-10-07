#!/usr/bin/env bash
# run.sh - Start FastAPI backend and Streamlit frontend concurrently

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "============================================================"
echo "🧠 Starting Local GitHub Repository Code Explainer"
echo "============================================================"

# Check if virtualenv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    /usr/local/bin/python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

# Verify Ollama is running
echo "Checking local Ollama status..."
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️ Warning: Ollama does not seem to be running on http://127.0.0.1:11434."
    echo "Please start Ollama in another terminal using: ollama serve"
fi

echo "Starting FastAPI Backend on http://127.0.0.1:8000..."
./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for FastAPI to initialize..."
sleep 2

echo "Starting Streamlit Frontend on http://localhost:8501..."
./venv/bin/streamlit run frontend/app.py --server.port 8501 --server.headless false &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "🚀 Application is running!"
echo "   • Frontend (Streamlit): http://localhost:8501"
echo "   • Backend (FastAPI):    http://127.0.0.1:8000"
echo "   • API Docs (Swagger):   http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to terminate both servers."
echo "============================================================"

# Graceful shutdown handler
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "Done."
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
