#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../dashboard"
export NEXT_PUBLIC_DEMO_MODE=true
echo "Starting We Law OS dashboard at http://127.0.0.1:3012"
npm run dev -- --hostname 127.0.0.1 --port 3012
