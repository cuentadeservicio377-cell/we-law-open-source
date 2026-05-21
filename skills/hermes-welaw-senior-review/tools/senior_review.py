"""Validation helpers for senior legal review packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REQUIRED_ARTIFACTS = (
    "SENIOR_REVIEW.md",
    "LEGAL_RISK_MEMO.md",
    "CLIENT_DELIVERY_DECISION.md",
)
STATUS_RE = re.compile(r"package_status\s*[:=]\s*`?([a-z-]+)`?", re.IGNORECASE)
BLOCKER_RE = re.compile(r"blocker_count\s*[:=]\s*(\d+)", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"placeholder_count\s*[:=]\s*(\d+)", re.IGNORECASE)


@dataclass
class SeniorReviewValidation:
    ok: bool
    package_status: str
    missing_files: list[str]
    invalid_files: list[str]
    blockers: list[str]
    blocker_count: int
    placeholder_count: int


def validate_senior_review_package(workspace: str | Path, *, require_signature_ready: bool = False) -> SeniorReviewValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []
    blockers: list[str] = []

    for name in ["SENIOR_REVIEW.md", "LEGAL_RISK_MEMO.md", "CLIENT_DELIVERY_DECISION.md"]:
        _require_nonempty(root / name, invalid)

    decision = _read_text(root / "CLIENT_DELIVERY_DECISION.md")
    package_status = _extract_status(decision)
    blocker_count = _extract_int(BLOCKER_RE, decision)
    placeholder_count = _extract_int(PLACEHOLDER_RE, decision)

    if not package_status:
        invalid.append("CLIENT_DELIVERY_DECISION.md must include package_status")
    if require_signature_ready and package_status != "signature-ready":
        blockers.append("package_status is not signature-ready")
    if package_status == "signature-ready" and blocker_count > 0:
        blockers.append("signature-ready package still has blockers")
    if package_status == "signature-ready" and placeholder_count > 0:
        blockers.append("signature-ready package still has placeholders")

    return SeniorReviewValidation(
        ok=not missing and not invalid and not blockers,
        package_status=package_status or "unknown",
        missing_files=missing,
        invalid_files=invalid,
        blockers=blockers,
        blocker_count=blocker_count,
        placeholder_count=placeholder_count,
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _require_nonempty(path: Path, invalid: list[str]) -> None:
    if path.exists() and not path.read_text(encoding="utf-8").strip():
        invalid.append(f"{path.name} is empty")


def _extract_status(text: str) -> str:
    match = STATUS_RE.search(text)
    return match.group(1).lower() if match else ""


def _extract_int(pattern: re.Pattern[str], text: str) -> int:
    match = pattern.search(text)
    return int(match.group(1)) if match else 0
