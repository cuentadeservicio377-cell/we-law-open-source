#!/usr/bin/env bash
set -euo pipefail
FULL="${1:-}"
python3 scripts/public_safety_scan.py
python3 scripts/doctor.py
python3 -m py_compile $(find runtime skills scripts -name '*.py' -type f | sort)
python3 runtime/scripts/bootstrap-paperclip-workers.py --dry-run >/tmp/welaw-paperclip-bootstrap-dry-run.json
python3 runtime/scripts/smoke-welaw-command-spine.py
python3 runtime/scripts/smoke-welaw-14-role-firm.py
python3 runtime/scripts/smoke-welaw-firm-workflow.py
python3 -m pytest -q
if [ "$FULL" = "--full" ]; then
  cd dashboard
  if [ -f package-lock.json ]; then npm ci; else npm install; fi
  npm run build
fi
