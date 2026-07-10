#!/bin/bash
# Launch the Refund Agent - choose your interface

set -e

cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Customer Refund Agent - Choose Your Interface         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  FastAPI Playground (Web UI + REST API)"
echo "    → Browser: http://localhost:8000"
echo "    → API: http://localhost:8000/api/refund"
echo ""
echo "2️⃣  Streamlit Dashboard (Interactive Dashboard)"
echo "    → Browser: http://localhost:8501"
echo ""
echo "Choose an option:"
read -p "Enter 1 or 2 (default: 1): " choice

choice=${choice:-1}

if [ "$choice" = "2" ]; then
    echo ""
    echo "🚀 Starting Streamlit dashboard..."
    echo "   Open: http://localhost:8501"
    echo ""
    streamlit run app.py --logger.level=error
else
    echo ""
    echo "🚀 Starting FastAPI playground..."
    echo "   Open: http://localhost:8000"
    echo ""
    python server.py
fi
