# Local Install

```bash
git clone https://github.com/cuentadeservicio377-cell/we-law-open-source.git <!-- public-safety: allow -->
cd we-law-open-source
python3 scripts/public_safety_scan.py
bash scripts/test.sh
cd dashboard
npm install
npm run build
NEXT_PUBLIC_DEMO_MODE=true npm run dev -- --hostname 127.0.0.1 --port 3012
```
