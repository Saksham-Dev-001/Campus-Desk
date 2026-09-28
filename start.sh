#!/usr/bin/env bash
# ====================================================================
#  CampusDesk — one-click launcher for Linux / macOS
# ====================================================================
set -e
cd "$(dirname "$0")"

echo ""
echo " ================================================================"
echo "   CampusDesk  -  College Information & Document Platform"
echo "   Team: Team Anonymous"
echo " ================================================================"
echo ""

if ! command -v python3 &>/dev/null; then
    echo " [ERROR] python3 not found. Install Python 3.10+ first."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo " [1/4] Creating virtual environment..."
    python3 -m venv .venv
else
    echo " [1/4] Virtual environment already exists."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo " [2/4] Installing dependencies..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo " [3/4] Creating .env from .env.example ..."
    cp .env.example .env
else
    echo " [3/4] .env already exists."
fi

echo " [4/4] Starting CampusDesk server..."
echo ""
echo " ----------------------------------------------------------------"
echo "  Open your browser at:  http://localhost:5000"
echo "  Admin: admin  |  Teacher: teacher1  |  password123"
echo "  Student: CSE2024001 (CSE A2) or CSE2024003 (CSE A1)"
echo " ----------------------------------------------------------------"
echo ""

if command -v xdg-open &>/dev/null; then xdg-open http://localhost:5000 &
elif command -v open &>/dev/null; then open http://localhost:5000 &
fi

python run.py
