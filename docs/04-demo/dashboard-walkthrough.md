# Dashboard Demo Walkthrough

Run:

```bash
bash scripts/setup.sh
bash scripts/demo.sh
```

Open http://127.0.0.1:3012.

## What To Inspect

1. **Home** — confirms the dashboard is a legal office surface, not a terminal. Look for active matters, blockers, worker status and approval prompts.
2. **Clientes** — open the synthetic Northstar Health Demo client. This proves client memory, matter status and document state can be visible to a non-technical lawyer.
3. **Matters** — inspect the health SaaS package. It should show document work, missing information and Senior Review blockers.
4. **Workspace** — verify the demo Workspace layer uses safe `demo://` references instead of live Drive links.
5. **Intake** — verify transcript-driven intake concepts: collected facts, missing data and next questions.
6. **Memoria** — verify reusable client memory and risks.
7. **Aprobaciones** — verify the system blocks delivery/signature until review gates pass.

## What The Demo Proves

The demo intentionally blocks final delivery. That is good. A legal OS should stop when tax/signature facts, ownership facts, review or editorial readiness are missing.
