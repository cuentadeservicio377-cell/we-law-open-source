"""Validation helpers for We Law expediente/paralegal work products."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = (
    "EXPEDIENTE_VIVO.md",
    "DOCUMENT_INDEX.json",
    "VERSION_LOG.md",
    "FOLDER_MANIFEST.json",
)


@dataclass
class FileWorkProductValidation:
    ok: bool
    missing_files: list[str]
    invalid_files: list[str]


def validate_file_work_product(workspace: str | Path) -> FileWorkProductValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []

    _require_nonempty(root / "EXPEDIENTE_VIVO.md", invalid)
    _require_nonempty(root / "VERSION_LOG.md", invalid)

    document_index = _read_json(root / "DOCUMENT_INDEX.json", invalid)
    folder_manifest = _read_json(root / "FOLDER_MANIFEST.json", invalid)

    if document_index is not None and not _has_list(document_index, "documents", "sources"):
        invalid.append("DOCUMENT_INDEX.json must include documents or sources")
    if folder_manifest is not None and not _has_list(folder_manifest, "folders"):
        invalid.append("FOLDER_MANIFEST.json must include folders")

    return FileWorkProductValidation(
        ok=not missing and not invalid,
        missing_files=missing,
        invalid_files=invalid,
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


def _has_list(data: Any, *keys: str) -> bool:
    if not isinstance(data, dict):
        return False
    return any(isinstance(data.get(key), list) and len(data[key]) > 0 for key in keys)
