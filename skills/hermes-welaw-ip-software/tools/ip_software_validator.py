"""Deterministic IP/software validator for We Law packets."""

from __future__ import annotations

from typing import Any


def validate_ip_software_packet(packet: dict[str, Any]) -> dict[str, Any]:
    text = str(packet.get("text") or packet.get("content") or "").lower()
    checks = {
        "repository_scope": any(token in text for token in ["repositorio", "repository", "github", "gitlab"]),
        "ip_ownership": any(token in text for token in ["propiedad intelectual", "cotitularidad", "obra por encargo", "cesión", "cesion"]),
        "third_party_components": any(token in text for token in ["open source", "tercero", "terceros", "licencia", "librería", "libreria"]),
        "deliverables": any(token in text for token in ["entregable", "desarrollo", "software", "saas"]),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "kind": "ip_software_validation",
        "status": "passed" if not missing else "needs_review",
        "checks": checks,
        "missing": missing,
        "required_artifacts": ["IP_OWNERSHIP_MATRIX.md", "SOFTWARE_SCOPE_LEDGER.json", "TECH_CONTRACT_QA.md"],
    }
