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

## Before You Contribute

Please read:

- docs/02-architecture/we-law-os.md
- docs/03-install-run/reinstall-any-computer.md
- docs/07-community/problems-we-need-help-solving.md

A good contribution should make the system more installable, more auditable, safer for client data, or easier for a lawyer to understand.

## Full Verification

Run the full local gate before pushing:

```bash
bash scripts/test.sh --full
```

This validates safety scan, doctor, Python compile, Paperclip worker dry-run, command-spine smoke, 14-role firm smoke, workflow smoke, pytest and dashboard build.
