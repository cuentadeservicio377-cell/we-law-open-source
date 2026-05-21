"""WeasyPrint editorial rendering contract for legal deliverables."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


KNOWN_WEASYPRINT_PATHS = (
    "/Users/local-user/Library/Python/3.9/bin/weasyprint",
    "${HOMEBREW_BIN:-/usr/local/bin}/weasyprint",
    "/usr/local/bin/weasyprint",
)


@dataclass(frozen=True)
class EditorialRenderPlan:
    """A render plan that can be stored in DELIVERABLE_MANIFEST.json."""

    source_path: str
    output_pdf_path: str
    profile_id: str
    engine: str
    page_size: str
    google_docs_source: str | None
    requires_editorial_qa: bool
    weasyprint_bin: str | None
    status: str

    def to_manifest_entry(self) -> dict[str, Any]:
        return {
            "name": Path(self.output_pdf_path).name,
            "type": "editorial_pdf",
            "source_path": self.source_path,
            "output_path": self.output_pdf_path,
            "google_docs_source": self.google_docs_source,
            "renderer": self.engine,
            "page_size": self.page_size,
            "reference_profile_id": self.profile_id,
            "requires_editorial_qa": self.requires_editorial_qa,
            "weasyprint_bin": self.weasyprint_bin,
            "status": self.status,
        }


def find_weasyprint() -> str | None:
    found = shutil.which("weasyprint")
    if found:
        return found
    for candidate in KNOWN_WEASYPRINT_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def build_editorial_render_plan(
    source_path: str | Path,
    output_pdf_path: str | Path,
    *,
    profile_id: str,
    google_docs_source: str | None = None,
    weasyprint_bin: str | None = None,
) -> EditorialRenderPlan:
    binary = weasyprint_bin if weasyprint_bin is not None else find_weasyprint()
    binary = binary or None
    return EditorialRenderPlan(
        source_path=str(source_path),
        output_pdf_path=str(output_pdf_path),
        profile_id=profile_id,
        engine="weasyprint" if binary else "weasyprint_unavailable",
        page_size="A4",
        google_docs_source=google_docs_source,
        requires_editorial_qa=True,
        weasyprint_bin=binary,
        status="planned" if binary else "blocked",
    )


def deliverable_manifest_for_render_plan(plan: EditorialRenderPlan) -> dict[str, Any]:
    return {
        "manifest_version": "1",
        "source_of_truth": "google_docs_live_file" if plan.google_docs_source else "local_source_file",
        "deliverables": [plan.to_manifest_entry()],
        "editorial_outputs": [plan.to_manifest_entry()],
    }


def write_render_manifest(plan: EditorialRenderPlan, output_path: str | Path) -> dict[str, Any]:
    manifest = deliverable_manifest_for_render_plan(plan)
    Path(output_path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def render_html_to_pdf(plan: EditorialRenderPlan) -> dict[str, Any]:
    """Render an HTML source to PDF with WeasyPrint A4.

    Google Docs remains the live legal source. This function creates only the
    polished editorial PDF deliverable and expects editorial_reference_qa to run
    before any client-deliverable claim.
    """

    if not plan.weasyprint_bin:
        return {
            "ok": False,
            "status": "blocked",
            "reason": "WeasyPrint is not available",
            "manifest_entry": plan.to_manifest_entry(),
        }

    source = Path(plan.source_path)
    if not source.exists():
        return {
            "ok": False,
            "status": "blocked",
            "reason": f"Source file not found: {source}",
            "manifest_entry": plan.to_manifest_entry(),
        }

    output = Path(plan.output_pdf_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [plan.weasyprint_bin, str(source), str(output), "--media-type", "print"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "status": "blocked",
            "reason": completed.stderr.strip() or "WeasyPrint render failed",
            "manifest_entry": plan.to_manifest_entry(),
        }

    entry = {
        **plan.to_manifest_entry(),
        "status": "rendered",
    }
    return {
        "ok": True,
        "status": "rendered",
        "manifest_entry": entry,
    }


def build_internal_review_package(
    drafts: list[dict[str, Any]],
    *,
    matter_id: str,
    output_root: str | Path,
) -> dict[str, Any]:
    """Plan an editorial package from operational drafts without claiming delivery."""

    accepted_states = {"borrador_operativo", "review", "borrador_casi_firmable", "listo_revision_cliente"}
    normalized = []
    blockers: list[str] = []
    for draft in drafts:
        state = str(draft.get("document_state") or draft.get("status") or "borrador_operativo")
        if state not in accepted_states:
            blockers.append(f"{draft.get('title', 'Documento')}: estado no aceptado para paquete interno ({state})")
        for blocker in draft.get("blockers", []) or []:
            blockers.append(str(blocker))
        normalized.append(
            {
                "title": draft.get("title") or "Documento sin titulo",
                "path": draft.get("path"),
                "document_state": state,
                "blockers": draft.get("blockers", []) or [],
            }
        )

    package_status = "internal_review_package" if blockers else "client_delivery_candidate"
    output = Path(output_root)
    editorial_spec = {
        "kind": "editorial_spec",
        "matter_id": matter_id,
        "package_status": package_status,
        "input_states": [item["document_state"] for item in normalized],
        "documents": normalized,
        "blockers": blockers,
    }
    render_manifest = {
        "kind": "render_manifest",
        "matter_id": matter_id,
        "status": "planned_internal_review" if blockers else "planned_client_delivery_candidate",
        "output_root": str(output),
        "documents": normalized,
    }
    visual_qa = "\n".join(
        [
            "# VISUAL QA",
            "",
            f"Matter: {matter_id}",
            f"Estado: {package_status}",
            "Este paquete puede renderizarse para revisión interna aunque existan blockers de firma.",
            "",
        ]
    )
    blocker_lines = [f"- {item}" for item in blockers] if blockers else ["- Sin blockers declarados por el paquete editorial."]
    client_delivery_links = "\n".join(
        [
            "# CLIENT DELIVERY LINKS",
            "",
            "Estado: NO ENTREGAR AL CLIENTE" if blockers else "Estado: candidato a entrega tras Senior Review",
            "Blockers:",
            *blocker_lines,
            "",
        ]
    )
    return {
        "kind": "internal_editorial_package",
        "matter_id": matter_id,
        "package_status": package_status,
        "client_delivery_allowed": not blockers,
        "signature_ready": False,
        "EDITORIAL_SPEC.json": editorial_spec,
        "RENDER_MANIFEST.json": render_manifest,
        "VISUAL_QA.md": visual_qa,
        "CLIENT_DELIVERY_LINKS.md": client_delivery_links,
    }
