# Google Workspace Layer

Google Workspace is the familiar legal office: Drive folders, Docs drafts, Sheets ledgers, Calendar events, Tasks and communications.

The public repo uses `demo://` URIs. A real installation should keep credentials and real Workspace IDs outside git. Workspace state should be reflected through manifests and Control Master rows so Hermes, Paperclip and the dashboard can reason over the same office surface.

## Read-Only Probe

A live deployment should first prove read-only access before writeback:

```bash
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/absolute/path/to/google-token.json
gws drive files list --params '{"pageSize":1}' --format json
```

Only after read-only probes work should Hermes create folders, Docs, Sheets rows or Calendar/Task entries. Keep all real IDs out of git.
