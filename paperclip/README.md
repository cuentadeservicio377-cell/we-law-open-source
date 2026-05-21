# Paperclip Layer

Paperclip is the structured staff/project ledger. We Law OS expects 14 legal workers, each with a role contract, required artifacts, blockers and closure semantics.

Use `config/paperclip-hermes-agents.json` and `runtime/scripts/bootstrap-paperclip-workers.py --dry-run` to inspect the public worker configuration. Live creation requires a running Paperclip server and local environment variables.

## Public Dry Run

```bash
python3 runtime/scripts/bootstrap-paperclip-workers.py --dry-run
```

Expected result: JSON payloads for 14 `hermes_local` workers. No server mutation happens in dry-run.

## Live Apply

Use live apply only after Paperclip is running and credentials are local:

```bash
export PAPERCLIP_API_URL=http://127.0.0.1:3100/api
export PAPERCLIP_API_KEY=your-local-dev-key
export PAPERCLIP_COMPANY_ID=your-company-id
python3 runtime/scripts/bootstrap-paperclip-workers.py --apply --company-id "$PAPERCLIP_COMPANY_ID" --if-exists update
```
