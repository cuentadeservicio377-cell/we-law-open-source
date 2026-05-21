"""Deadline ledger and risk validation for We Law."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEFAULT_TIMEZONE = "America/Mexico_City"
REQUIRED_ARTIFACTS = (
    "DEADLINE_REGISTER.json",
    "DEADLINE_RISK_REPORT.md",
    "CALENDAR_SYNC_PLAN.md",
)


@dataclass
class DeadlineLedgerValidation:
    ok: bool
    missing_files: list[str]
    invalid_items: list[str]
    high_risk: list[str]


def build_deadline_record(
    *,
    matter_id: str,
    name: str,
    due_date: str,
    source: str,
    calculation_basis: str,
    legal_basis: str,
    confidence: float,
    timezone: str = DEFAULT_TIMEZONE,
    reminder_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "matter_id": matter_id,
        "name": name,
        "due_date": due_date,
        "source": source,
        "calculation_basis": calculation_basis,
        "legal_basis": legal_basis,
        "timezone": timezone,
        "confidence": confidence,
        "reminder_policy": reminder_policy or {"days_before": [7, 3, 1], "same_day": true_value()},
        "risk_level": risk_level(confidence=confidence, legal_basis=legal_basis),
    }


def validate_deadline_ledger(workspace: str | Path) -> DeadlineLedgerValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []
    high_risk: list[str] = []

    register = _read_json(root / "DEADLINE_REGISTER.json", invalid)
    deadlines = register.get("deadlines", []) if isinstance(register, dict) else []
    if register is not None and not isinstance(deadlines, list):
        invalid.append("DEADLINE_REGISTER.json deadlines must be a list")
        deadlines = []

    for item in deadlines:
        name = str(item.get("name", "deadline"))
        for key in ["matter_id", "due_date", "source", "calculation_basis", "timezone"]:
            if not item.get(key):
                invalid.append(f"{name} missing {key}")
        if not item.get("legal_basis"):
            invalid.append(f"{name} missing legal_basis")
        if item.get("risk_level") == "high" or float(item.get("confidence", 0)) < 0.7:
            high_risk.append(name)

    _require_nonempty(root / "DEADLINE_RISK_REPORT.md", invalid)
    _require_nonempty(root / "CALENDAR_SYNC_PLAN.md", invalid)

    return DeadlineLedgerValidation(
        ok=not missing and not invalid,
        missing_files=missing,
        invalid_items=invalid,
        high_risk=high_risk,
    )


def risk_level(*, confidence: float, legal_basis: str) -> str:
    if confidence < 0.7 or not legal_basis or legal_basis == "por confirmar":
        return "high"
    if confidence < 0.9:
        return "medium"
    return "medium"


def _read_json(path: Path, invalid: list[str]) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        invalid.append(f"{path.name} invalid JSON: {exc.msg}")
        return None


def _require_nonempty(path: Path, invalid: list[str]) -> None:
    if path.exists() and not path.read_text(encoding="utf-8").strip():
        invalid.append(f"{path.name} is empty")


def true_value() -> bool:
    return True
