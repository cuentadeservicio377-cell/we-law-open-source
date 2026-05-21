#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['README.md','dashboard/package.json','data/clients.json','data/matters.json','fixtures/demo/transcripts/initial-intake.md','config/legal-worker-operating-contract.json','skills/hermes-welaw-core/SKILL.md','workspace/brain/index.md','scripts/public_safety_scan.py']
def ok(label): print(f'OK  {label}')
def fail(label): raise SystemExit(f'FAIL {label}')
def version_tuple(text):
    import re
    match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', text)
    return tuple(int(value or 0) for value in match.groups()) if match else (0, 0, 0)
def run_output(cmd): return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
def check_core():
    for rel in REQUIRED:
        if not (ROOT / rel).exists(): fail(f"missing {rel}")
        ok(f"found {rel}")
    if sys.version_info < (3, 9): fail('Python 3.9+ required')
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    for bin_name in ['node', 'npm', 'git']:
        if not shutil.which(bin_name): fail(f"{bin_name} not found")
        ok(f"{bin_name} available")
    if version_tuple(run_output(['node', '--version'])) < (20, 0, 0): fail('Node.js 20+ required')
    ok('Node.js 20+')
    try:
        import pytest  # noqa: F401
        ok('pytest available')
    except Exception:
        fail('pytest not installed; run python3 -m pip install -r requirements-dev.txt')
    clients = json.loads((ROOT / 'data/clients.json').read_text())
    matters = json.loads((ROOT / 'data/matters.json').read_text())
    if not clients or not matters: fail('demo client and matter data required')
    ok('demo data loaded')
    roles = json.loads((ROOT / 'config/firm-operating-model.json').read_text()).get('roles', {})
    if len(roles) < 14: fail('expected at least 14 firm roles')
    ok(f"{len(roles)} firm roles configured")
    subprocess.run(['python3', 'scripts/public_safety_scan.py'], cwd=ROOT, check=True)
    ok('public safety scan passed')
def check_live():
    print('Live integration checks are optional and read-only where possible.')
    for bin_name in ['hermes', 'gws']:
        found = shutil.which(bin_name)
        print(('OK  ' if found else 'WARN ') + (f'{bin_name} found at {found}' if found else f'{bin_name} not found on PATH'))
    api_url = os.environ.get('PAPERCLIP_API_URL', 'http://127.0.0.1:3100/api').rstrip('/')
    try:
        with request.urlopen(f'{api_url}/health', timeout=3) as response:
            ok(f'Paperclip health HTTP {response.status}')
    except Exception as exc:
        print(f'WARN Paperclip health unavailable at {api_url}: {exc}')
    subprocess.run(['python3', 'runtime/scripts/bootstrap-paperclip-workers.py', '--dry-run'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    ok('Paperclip worker bootstrap dry-run passed')
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Also check optional Hermes/Paperclip/Google live integration prerequisites.')
    args = parser.parse_args()
    check_core()
    if args.live: check_live()
    print('We Law OS public repo doctor passed.')
if __name__ == '__main__': main()
