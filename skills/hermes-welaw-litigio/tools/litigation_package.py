"""Validation helpers for We Law litigation work products."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = (
    "CASE_THEORY.md",
    "PROCEDURAL_POSTURE.md",
    "EVIDENCE_TABLE.md",
    "FILING_PACKAGE_MANIFEST.json",
    "DEADLINE_RISK.md",
)


@dataclass
class LitigationPackageValidation:
    ok: bool
    missing_files: list[str]
    invalid_files: list[str]


def validate_litigation_package(workspace: str | Path) -> LitigationPackageValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []

    for name in ["CASE_THEORY.md", "PROCEDURAL_POSTURE.md", "EVIDENCE_TABLE.md", "DEADLINE_RISK.md"]:
        _require_nonempty(root / name, invalid)

    evidence = _read_text(root / "EVIDENCE_TABLE.md").lower()
    if evidence and ("hecho" not in evidence or "fuente" not in evidence):
        invalid.append("EVIDENCE_TABLE.md must include hecho and fuente columns")

    manifest = _read_json(root / "FILING_PACKAGE_MANIFEST.json", invalid)
    if manifest is not None and not _has_files(manifest):
        invalid.append("FILING_PACKAGE_MANIFEST.json must include files")

    deadline_risk = _read_text(root / "DEADLINE_RISK.md").lower()
    if deadline_risk and "legal_basis" not in deadline_risk:
        invalid.append("DEADLINE_RISK.md must include legal_basis")

    return LitigationPackageValidation(
        ok=not missing and not invalid,
        missing_files=missing,
        invalid_files=invalid,
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


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


def _has_files(manifest: Any) -> bool:
    return isinstance(manifest, dict) and isinstance(manifest.get("files"), list) and len(manifest["files"]) > 0
