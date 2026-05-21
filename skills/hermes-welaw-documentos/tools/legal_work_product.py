"""Validation helpers for We Law legal-document work products."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


REQUIRED_ARTIFACTS = (
    "EVIDENCE_MAP.md",
    "DATA_LEDGER.json",
    "CORRECTIONS_APPLIED.md",
    "PLACEHOLDER_REPORT.md",
    "DELIVERABLE_MANIFEST.json",
    "LEGAL_QA.md",
)
LEGAL_BASIS_ARTIFACT = "LEGAL_BASIS_MEMO.md"
CROSS_DOCUMENT_REVIEW_ARTIFACT = "CROSS_DOCUMENT_REVIEW.md"
EDITORIAL_QA_ARTIFACT = "EDITORIAL_REFERENCE_QA.json"

FINAL_STATUSES = {"client-deliverable", "signature-ready"}
PLACEHOLDER_RE = re.compile(r"\[(?:PENDIENTE|CONFIRMAR|DEFINIR|NOMBRE|RFC|DOMICILIO|TEL|URL|PRECIO)[^\]]*\]", re.IGNORECASE)
STATUS_RE = re.compile(r"package_status\s*[:=]\s*`?([a-z-]+)`?", re.IGNORECASE)


@dataclass
class LegalWorkProductValidation:
    ok: bool
    package_status: str
    missing_files: list[str]
    invalid_files: list[str]
    blockers: list[str]
    placeholder_count: int
    editorial_qa_required: bool = False
    editorial_qa_ok: bool = False


def validate_legal_work_product(workspace: str | Path, *, require_signature_ready: bool = False) -> LegalWorkProductValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []
    blockers: list[str] = []

    data_ledger = _read_json(root / "DATA_LEDGER.json", invalid)
    manifest = _read_json(root / "DELIVERABLE_MANIFEST.json", invalid)
    editorial_qa = _read_json(root / EDITORIAL_QA_ARTIFACT, invalid)
    package_status = _package_status(root / "LEGAL_QA.md")
    placeholder_count = _placeholder_count(root / "PLACEHOLDER_REPORT.md")

    _require_nonempty(root / "EVIDENCE_MAP.md", invalid)
    _require_nonempty(root / "CORRECTIONS_APPLIED.md", invalid)
    _require_nonempty(root / "PLACEHOLDER_REPORT.md", invalid)
    _require_nonempty(root / "LEGAL_QA.md", invalid)

    if data_ledger is not None and not isinstance(data_ledger, dict):
        invalid.append("DATA_LEDGER.json must be a JSON object")
    if manifest is not None and not _has_deliverables(manifest):
        invalid.append("DELIVERABLE_MANIFEST.json must include deliverables")
    if not package_status:
        invalid.append("LEGAL_QA.md must include package_status")
    if require_signature_ready and package_status != "signature-ready":
        blockers.append("package_status is not signature-ready")
    if package_status in FINAL_STATUSES and placeholder_count > 0:
        blockers.append(f"{package_status} package still has placeholders")

    editorial_qa_required = bool(
        package_status in FINAL_STATUSES and manifest is not None and _requires_editorial_qa(manifest)
    )
    editorial_qa_ok = bool(isinstance(editorial_qa, dict) and editorial_qa.get("ok") is True)
    if editorial_qa_required:
        if not (root / EDITORIAL_QA_ARTIFACT).exists():
            blockers.append(f"{package_status} package requires {EDITORIAL_QA_ARTIFACT}")
        elif not editorial_qa_ok:
            blockers.append(f"{EDITORIAL_QA_ARTIFACT} did not pass")

    if package_status in FINAL_STATUSES and manifest is not None:
        blockers.extend(_dishonest_drive_status_blockers(manifest))
        if not _nonempty_file(root / LEGAL_BASIS_ARTIFACT):
            blockers.append(f"{package_status} package requires {LEGAL_BASIS_ARTIFACT}")
        if _requires_cross_document_review(manifest) and not _nonempty_file(root / CROSS_DOCUMENT_REVIEW_ARTIFACT):
            blockers.append(f"{package_status} package requires {CROSS_DOCUMENT_REVIEW_ARTIFACT}")

    ok = not missing and not invalid and not blockers
    return LegalWorkProductValidation(
        ok=ok,
        package_status=package_status or "unknown",
        missing_files=missing,
        invalid_files=invalid,
        blockers=blockers,
        placeholder_count=placeholder_count,
        editorial_qa_required=editorial_qa_required,
        editorial_qa_ok=editorial_qa_ok,
    )


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


def _nonempty_file(path: Path) -> bool:
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _has_deliverables(data: Any) -> bool:
    if isinstance(data, list):
        return len(data) > 0
    if isinstance(data, dict):
        deliverables = data.get("deliverables") or data.get("documents") or data.get("files") or data.get("outputs")
        return isinstance(deliverables, list) and len(deliverables) > 0
    return False


def _requires_editorial_qa(data: Any) -> bool:
    entries = _manifest_entries(data)
    return any(entry.get("requires_editorial_qa") is True for entry in entries)


def _requires_cross_document_review(data: Any) -> bool:
    entries = _manifest_entries(data)
    document_types = {entry.get("document_type") or entry.get("type") or entry.get("name") for entry in entries}
    return len({item for item in document_types if item}) > 1


def _dishonest_drive_status_blockers(data: Any) -> list[str]:
    blockers: list[str] = []
    for entry in _manifest_entries(data):
        status = str(
            entry.get("drive_upload_status")
            or entry.get("google_docs_status")
            or entry.get("workspace_write_status")
            or ""
        ).lower()
        claims_live_write = status in {"uploaded", "published", "live", "updated", "created"}
        has_link = any(
            entry.get(key)
            for key in (
                "url",
                "link",
                "drive_url",
                "google_doc_url",
                "google_docs_source",
                "webViewLink",
            )
        )
        if claims_live_write and not has_link:
            blockers.append(f"{entry.get('name', 'deliverable')} claims {status} without live link")
    return blockers


def _manifest_entries(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if not isinstance(data, dict):
        return []
    entries: list[dict[str, Any]] = []
    for key in ("deliverables", "documents", "files", "outputs", "editorial_outputs"):
        value = data.get(key)
        if isinstance(value, list):
            entries.extend(entry for entry in value if isinstance(entry, dict))
    return entries


def _package_status(path: Path) -> str:
    if not path.exists():
        return ""
    match = STATUS_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).lower() if match else ""


def _placeholder_count(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    explicit = re.search(r"placeholder_count\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if explicit:
        return int(explicit.group(1))
    total = re.search(r"total\s+de\s+placeholders[^:]*:\s*(\d+)", text, re.IGNORECASE)
    if total:
        return int(total.group(1))
    return len(PLACEHOLDER_RE.findall(text))
