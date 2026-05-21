# Contributing

Thank you for helping We Law Open Source. The best contributions make the system safer, more understandable and easier for a lawyer to supervise.

Good areas to help:

- Synthetic legal fixtures and expected outputs.
- Dashboard UX for non-technical lawyers.
- Worker contracts, tool boundaries and artifact gates.
- Paperclip adapter examples.
- Google Workspace dry-run and live-sync adapters.
- Legal Brain schemas and audit trails.
- Security, privacy and sanitization tests.

Before opening a PR, run:

```bash
bash scripts/test.sh
cd dashboard && npm run build
```

Do not include real client files, private Drive links, tokens, personal local paths or production runtime logs.
