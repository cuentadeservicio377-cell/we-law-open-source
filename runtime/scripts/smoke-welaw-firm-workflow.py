#!/usr/bin/env python3
"""Offline smoke for synthetic We Law firm workflows."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests/fixtures/firm_workflows"
sys.path.insert(0, str(ROOT / "skills" / "hermes-welaw-core" / "tools"))

from firm_model import load_firm_model


def load_fixtures() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURE_DIR.glob("*.json"))]


def validate_fixture(fixture: dict, firm_model: dict) -> list[str]:
    errors = []
    roles = firm_model["roles"]
    for step in fixture.get("steps", []):
        role = step.get("role")
        if role not in roles:
            errors.append(f"{fixture['id']} unknown role {role}")
            continue
        expected_prefix = roles[role]["paperclipCommentPrefix"]
        if step.get("expected_prefix") != expected_prefix:
            errors.append(f"{fixture['id']} {role} expected prefix mismatch")
        rendered = json.dumps(step)
        if "HERMES LIVE OK" in rendered:
            errors.append(f"{fixture['id']} contains smoke-only text")
        if not step.get("required_artifacts"):
            errors.append(f"{fixture['id']} {role} missing required_artifacts")
    return errors


def main() -> int:
    firm_model = load_firm_model(ROOT / "config/firm-operating-model.json")
    fixtures = load_fixtures()
    errors = []
    if len(firm_model["roles"]) != 14:
        errors.append(f"firm model expected 14 roles, found {len(firm_model['roles'])}")
    for fixture in fixtures:
        errors.extend(validate_fixture(fixture, firm_model))
    result = {"ok": not errors, "role_count": len(firm_model["roles"]), "fixture_count": len(fixtures), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
