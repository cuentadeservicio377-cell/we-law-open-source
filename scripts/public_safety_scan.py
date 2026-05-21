#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
SKIP_DIRS = {'.git','node_modules','.next','__pycache__','.pytest_cache'}
SKIP_SUFFIXES = {'.png','.jpg','.jpeg','.gif','.webp','.ico','.lock'}
SKIP_FILES = {'scripts/public_safety_scan.py'}
PATTERNS = [
    ('private_macos_user_path', re.compile(r'/Users/(?!example|local-user|your-user|runner|Shared)[A-Za-z0-9._ -]+')),
    ('real_google_workspace_url', re.compile(r'https://(?:drive|docs|sheets)\.google\.com/[^\s)"\']+')),
    ('real_workspace_id', re.compile(r'/(?:document|spreadsheets|folders)/d?/([A-Za-z0-9_-]{20,})')),
    ('email_address', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
    ('live_wel_issue', re.compile(r'\bWEL-\d+(?:-\d+|\.\.\d+|\.\.WEL-\d+)?\b')),
    ('real_client_name', re.compile(r'\b(?:Medialergias|Proyecto Alergias|Minerva|Aleyda|Benjamin|Oscar|Elias|Fernandez|Padilla)\b', re.I)),
    ('private_account', re.compile(r'pablomeneses|Pablo')),
    ('known_drive_id', re.compile(r'1L4-7OOG|1i6apy|1DzXQVDT|1DyCmhHo|1Sa6Zfl0')),
    ('literal_bearer_secret', re.compile(r'(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}')),
    ('literal_secret_value', re.compile(r"(?i)(refresh_token|access_token|client_secret|telegram_token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}")),
]
ALLOW_LINE = 'public-safety: allow'
violations = []
for path in ROOT.rglob('*'):
    if any(part in SKIP_DIRS for part in path.parts):
        continue
    if str(path.relative_to(ROOT)) in SKIP_FILES:
        continue
    if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_LINE in line:
            continue
        for name, pattern in PATTERNS:
            if pattern.search(line):
                violations.append(f'{path.relative_to(ROOT)}:{lineno}: {name}: {line[:180]}')
if violations:
    print('Public safety scan failed:')
    print('\n'.join(violations[:200]))
    if len(violations) > 200:
        print(f'... {len(violations)-200} more')
    sys.exit(1)
print('Public safety scan passed.')
