"""Editorial PDF reference QA for We Law legal deliverables."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


A4_WIDTH_PT = 595.0
A4_HEIGHT_PT = 842.0
A4_TOLERANCE_PT = 8.0


@dataclass(frozen=True)
class PdfMetadata:
    """Small PDF metadata subset needed for editorial quality gates."""

    pages: int
    page_width_pt: float
    page_height_pt: float
    producer: str


@dataclass(frozen=True)
class ReferenceProfile:
    """Expected PDF profile for a polished legal deliverable."""

    profile_id: str
    label: str
    min_pages: int
    expected_page_size: str = "A4"
    required_producer: str = "WeasyPrint"
    block_compressed_output: bool = True


MAT005_REFERENCE_PROFILES = {
    "mat005_tyc": ReferenceProfile(
        profile_id="mat005_tyc",
        label="MAT-DEMO-001 Terminos y Condiciones Kami reference",
        min_pages=6,
    ),
    "mat005_aviso_privacidad_integral": ReferenceProfile(
        profile_id="mat005_aviso_privacidad_integral",
        label="MAT-DEMO-001 Aviso de Privacidad Integral Kami reference",
        min_pages=8,
    ),
}


class EditorialReferenceQaError(ValueError):
    """Raised when PDF metadata cannot be read or parsed."""


def profile_for_document(profile_id: str) -> ReferenceProfile:
    try:
        return MAT005_REFERENCE_PROFILES[profile_id]
    except KeyError as exc:
        raise EditorialReferenceQaError(f"Unknown editorial reference profile: {profile_id}") from exc


def read_pdf_metadata(pdf_path: str | Path, pdfinfo_bin: str | None = None) -> PdfMetadata:
    """Read PDF metadata using pdfinfo and return the fields needed for QA."""

    path = Path(pdf_path)
    if not path.exists():
        raise EditorialReferenceQaError(f"PDF not found: {path}")

    binary = pdfinfo_bin or shutil.which("pdfinfo")
    if not binary:
        raise EditorialReferenceQaError("pdfinfo is required for editorial reference QA")

    completed = subprocess.run(
        [binary, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise EditorialReferenceQaError(completed.stderr.strip() or "pdfinfo failed")
    return parse_pdfinfo_output(completed.stdout)


def parse_pdfinfo_output(output: str) -> PdfMetadata:
    pages = _extract_int(output, "Pages")
    producer = _extract_string(output, "Producer")
    width, height = _extract_page_size(output)
    return PdfMetadata(
        pages=pages,
        page_width_pt=width,
        page_height_pt=height,
        producer=producer,
    )


def evaluate_pdf_metadata(metadata: PdfMetadata, profile: ReferenceProfile) -> dict[str, Any]:
    """Evaluate metadata against a reference profile and return a manifest-safe result."""

    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "id": "minimum_page_count",
            "ok": metadata.pages >= profile.min_pages,
            "observed": metadata.pages,
            "expected": f">= {profile.min_pages}",
        }
    )

    checks.append(
        {
            "id": "page_size_a4",
            "ok": _is_a4(metadata.page_width_pt, metadata.page_height_pt),
            "observed": f"{metadata.page_width_pt:.2f} x {metadata.page_height_pt:.2f} pt",
            "expected": profile.expected_page_size,
        }
    )

    producer_ok = profile.required_producer.lower() in metadata.producer.lower()
    checks.append(
        {
            "id": "renderer",
            "ok": producer_ok,
            "observed": metadata.producer,
            "expected": profile.required_producer,
        }
    )

    compressed_ok = True
    if profile.block_compressed_output:
        compressed_ok = metadata.pages >= profile.min_pages and producer_ok
    checks.append(
        {
            "id": "compressed_output_guard",
            "ok": compressed_ok,
            "observed": {
                "pages": metadata.pages,
                "producer": metadata.producer,
            },
            "expected": "not compressed against reference floor",
        }
    )

    ok = all(check["ok"] for check in checks)
    return {
        "ok": ok,
        "profile_id": profile.profile_id,
        "profile_label": profile.label,
        "metadata": {
            "pages": metadata.pages,
            "page_width_pt": metadata.page_width_pt,
            "page_height_pt": metadata.page_height_pt,
            "producer": metadata.producer,
        },
        "checks": checks,
        "status": "passed" if ok else "failed",
    }


def evaluate_pdf(pdf_path: str | Path, profile_id: str) -> dict[str, Any]:
    profile = profile_for_document(profile_id)
    metadata = read_pdf_metadata(pdf_path)
    result = evaluate_pdf_metadata(metadata, profile)
    result["pdf_path"] = str(pdf_path)
    return result


def write_editorial_reference_qa(
    pdf_path: str | Path,
    profile_id: str,
    output_path: str | Path,
) -> dict[str, Any]:
    result = evaluate_pdf(pdf_path, profile_id)
    Path(output_path).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def evaluate_deliverable_manifest_freshness(
    manifest: dict[str, Any],
    *,
    current_output_root: str | Path,
) -> dict[str, Any]:
    """Verify a legal deliverable manifest points to fresh current-run artifacts.

    Historical WEL outputs may be listed as `historical_sources`, but the current
    manifest must include at least one existing artifact under the current issue
    output root. This keeps Paperclip workers from closing new document work by
    simply pointing at old DEMO-ISSUE folders.
    """

    root = Path(current_output_root).resolve()
    artifact_paths = _manifest_paths(manifest.get("artifacts", []))
    historical_paths = set(_manifest_paths(manifest.get("historical_sources", [])))
    missing_paths = [str(path) for path in artifact_paths if not path.exists()]
    fresh_paths = [
        path
        for path in artifact_paths
        if path.exists() and _is_relative_to(path.resolve(), root) and path not in historical_paths
    ]
    failed_checks: list[str] = []
    if missing_paths:
        failed_checks.append("manifest_paths_must_exist")
    if not fresh_paths:
        failed_checks.append("fresh_current_output")
    old_active_paths = [
        str(path)
        for path in artifact_paths
        if path.exists() and path not in historical_paths and not _is_relative_to(path.resolve(), root)
    ]
    if old_active_paths:
        failed_checks.append("old_wel_output_declared_as_active")
    return {
        "ok": not failed_checks,
        "status": "passed" if not failed_checks else "failed",
        "current_output_root": str(root),
        "fresh_artifacts": [str(path) for path in fresh_paths],
        "missing_paths": missing_paths,
        "old_active_paths": old_active_paths,
        "failed_checks": failed_checks,
    }


def _extract_int(output: str, key: str) -> int:
    match = re.search(rf"^{re.escape(key)}:\s*(\d+)\s*$", output, flags=re.MULTILINE)
    if not match:
        raise EditorialReferenceQaError(f"Missing pdfinfo field: {key}")
    return int(match.group(1))


def _extract_string(output: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", output, flags=re.MULTILINE)
    return match.group(1) if match else ""


def _extract_page_size(output: str) -> tuple[float, float]:
    match = re.search(
        r"^Page size:\s*([0-9.]+)\s+x\s+([0-9.]+)\s+pts",
        output,
        flags=re.MULTILINE,
    )
    if not match:
        raise EditorialReferenceQaError("Missing pdfinfo field: Page size")
    return float(match.group(1)), float(match.group(2))


def _is_a4(width: float, height: float) -> bool:
    pairs = [(width, height), (height, width)]
    return any(
        abs(candidate_width - A4_WIDTH_PT) <= A4_TOLERANCE_PT
        and abs(candidate_height - A4_HEIGHT_PT) <= A4_TOLERANCE_PT
        for candidate_width, candidate_height in pairs
    )


def _manifest_paths(items: Any) -> list[Path]:
    paths: list[Path] = []
    if not isinstance(items, list):
        return paths
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get("path")
        if isinstance(value, str) and value:
            paths.append(Path(value).resolve())
    return paths


def _is_relative_to(path_value: Path, root: Path) -> bool:
    try:
        path_value.relative_to(root)
        return True
    except ValueError:
        return False
