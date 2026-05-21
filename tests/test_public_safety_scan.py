from pathlib import Path
import subprocess
import sys


def test_public_safety_scan_passes_repo():
    result = subprocess.run([sys.executable, 'scripts/public_safety_scan.py'], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_demo_fixture_exists():
    assert Path('fixtures/demo/clients/CLI-DEMO-HEALTH.json').exists()
    assert Path('fixtures/demo/transcripts/initial-intake.md').exists()
