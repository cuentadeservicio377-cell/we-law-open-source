#!/usr/bin/env bash
set -euo pipefail
python3 scripts/public_safety_scan.py
python3 -m pytest -q
