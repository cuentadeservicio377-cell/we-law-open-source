# Install We Law OS On A Fresh Computer

This guide is for a contributor who wants to clone the public repository and run the complete demo locally.

## Requirements

- Git
- Python 3.9+
- Node.js 20+
- npm

Optional live integrations:

- Hermes CLI
- Paperclip server
- Google Workspace CLI / credentials

## 1. Clone

```bash
git clone https://github.com/cuentadeservicio377-cell/we-law-open-source.git
cd we-law-open-source
```

## 2. Run Setup

```bash
bash scripts/setup.sh
```

Setup checks Python/Node/npm, runs the public safety scanner, installs dashboard dependencies and builds the dashboard.

## 3. Run Demo Dashboard

```bash
bash scripts/demo.sh
```

Open http://127.0.0.1:3012.

## 4. What You Should See

The dashboard should show a synthetic client called Northstar Health Demo LLC and a blocked health SaaS legal package. The block is intentional: it demonstrates that the system should not pretend a legal package is ready when signature facts, ownership facts or cross-document review are missing.

## 5. Run Tests

```bash
bash scripts/test.sh
```

## 6. Enable Live Integrations Later

Copy `.env.example` to `.env` and follow [live-integrations.md](live-integrations.md). The demo does not require live credentials.
