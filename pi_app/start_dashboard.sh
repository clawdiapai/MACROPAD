#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing/verifying Python dependencies..."
python3 -m pip install -r requirements.txt

echo "Starting MacroPad Web Dashboard on port 5000..."
python3 app.py
