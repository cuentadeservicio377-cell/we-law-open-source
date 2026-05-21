"""Deterministic privacy/compliance validator for We Law packets."""

from __future__ import annotations

from typing import Any


def validate_privacy_packet(packet: dict[str, Any]) -> dict[str, Any]:
    text = str(packet.get("text") or packet.get("content") or "").lower()
    checks = {
        "personal_data": any(token in text for token in ["dato personal", "datos personales", "sensible", "sensibles"]),
        "arco": "arco" in text,
        "transfers": any(token in text for token in ["transferencia", "transferencias", "encargado", "responsable"]),
        "purposes": any(token in text for token in ["finalidad", "finalidades", "propósito", "proposito"]),
    }
    missing = [name for name, ok in checks.items() if not ok]
    status = "passed" if not missing else "needs_review"
    if not checks["personal_data"]:
        status = "blocked"
    return {
        "kind": "privacy_validation",
        "status": status,
        "checks": checks,
        "missing": missing,
        "required_artifacts": ["PRIVACY_DATA_MAP.json", "COMPLIANCE_MATRIX.md", "ARCO_CHECKLIST.md", "PRIVACY_QA.md"],
    }
