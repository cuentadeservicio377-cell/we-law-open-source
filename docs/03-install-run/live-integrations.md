# Live Hermes, Paperclip And Google Workspace Integrations

The public repo is offline-first. Live integrations are opt-in. This is deliberate: public open-source code must not ship real credentials, client folders or production runtime state.

## Environment

Copy the example file:

```bash
cp .env.example .env
```

Set values for your machine:

```bash
HERMES_COMMAND=hermes
HERMES_WELAW_ROOT=/absolute/path/to/we-law-open-source
PAPERCLIP_API_URL=http://127.0.0.1:3100/api
PAPERCLIP_API_KEY=your-local-dev-key
GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/absolute/path/to/google-token.json
ENABLE_LIVE_PROBES=false
NEXT_PUBLIC_DEMO_MODE=true
```

## Hermes

Install Hermes separately, then point it at this repository's `skills/`, `config/`, `schemas/` and `workspace/brain/` directories. Hermes should act as Managing Partner: it receives instructions, resolves context, reads the Legal Brain, creates command records and coordinates workers.

## Paperclip

Run Paperclip separately, then use `runtime/scripts/bootstrap-paperclip-workers.py --dry-run` to inspect the 14-worker setup. When connected to a local Paperclip server, the same script can create/update workers using environment variables from `.env`.

## Google Workspace

Google Workspace credentials are local-only. The public repo uses `demo://` URIs. A real deployment should map Drive folders, Docs and Sheets into Workspace manifests and Control Master rows without committing any of those IDs.

## Trust Rule

Live mode should never bypass the lawyer. Hermes can prepare work, Paperclip can execute tasks, Workspace can hold artifacts, but delivery, filing, signature and client communications need approval gates.

## Verifiable Commands

Check the public repo first:

```bash
python3 scripts/doctor.py
bash scripts/test.sh
python3 runtime/scripts/bootstrap-paperclip-workers.py --dry-run
```

Check optional live prerequisites:

```bash
python3 scripts/doctor.py --live
```

Create/update Paperclip workers only after live health checks pass:

```bash
python3 runtime/scripts/bootstrap-paperclip-workers.py \
  --apply \
  --api-url "$PAPERCLIP_API_URL" \
  --company-id "$PAPERCLIP_COMPANY_ID" \
  --if-exists update
```
