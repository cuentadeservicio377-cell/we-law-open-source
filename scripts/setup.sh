#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements-dev.txt
python3 scripts/doctor.py
cd dashboard
if [ -f package-lock.json ]; then npm ci; else npm install; fi
npm run build
cd ..
echo "We Law OS setup complete."
echo "Run: bash scripts/demo.sh"
