"""Cross-document review for We Law legal packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKAGE_TOPICS = [
    "parties",
    "dates",
    "amounts",
    "privacy_roles",
    "ip_ownership",
    "software_scope",
]


def build_package_cross_review(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a package-level consistency review from document manifests."""

    documents = [_normalize_manifest(item) for item in manifests]
    checks = {topic: _topic_check(documents, topic) for topic in PACKAGE_TOPICS}
    checks["placeholders"] = _placeholder_check(documents)
    blocked = any(check["status"] == "blocked" for check in checks.values())
    needs_review = any(check["status"] == "review" for check in checks.values())
    status = "blocked" if blocked else "needs_partner_review" if needs_review else "passed"
    return {
        "kind": "package_cross_review",
        "status": status,
        "document_count": len(documents),
        "documents": documents,
        "checks": checks,
        "required_outputs": ["PACKAGE_CROSS_REVIEW.md", "PACKAGE_CROSS_REVIEW.json"],
    }


def write_package_cross_review(manifests: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    review = build_package_cross_review(manifests)
    json_path = output / "PACKAGE_CROSS_REVIEW.json"
    markdown_path = output / "PACKAGE_CROSS_REVIEW.md"
    json_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_package_cross_review_markdown(review), encoding="utf-8")
    return {**review, "json_path": str(json_path), "markdown_path": str(markdown_path)}


def render_package_cross_review_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# REVISION CRUZADA",
        "",
        f"Estado final: {review['status']}",
        f"Documentos revisados: {review['document_count']}",
        "",
        "## Hallazgos",
    ]
    for topic, check in review["checks"].items():
        lines.append(f"- {topic}: {check['status']} ({check['summary']})")
    lines.extend(["", "## Pendientes de cierre"])
    blockers = [
        f"{topic}: {item}"
        for topic, check in review["checks"].items()
        for item in check.get("blockers", [])
    ]
    lines.extend([f"- {item}" for item in blockers] or ["- Sin blockers detectados por este motor."])
    lines.append("")
    return "\n".join(lines)


def _normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    ledger = manifest.get("data_ledger", {})
    placeholders = manifest.get("placeholder_report", [])
    return {
        "document_type": manifest.get("document_type") or manifest.get("type") or "unknown",
        "title": manifest.get("title") or manifest.get("name") or "Documento sin titulo",
        "data_ledger": {
            topic: _as_list(ledger.get(topic))
            for topic in PACKAGE_TOPICS
        },
        "placeholders": placeholders if isinstance(placeholders, list) else [],
    }


def _topic_check(documents: list[dict[str, Any]], topic: str) -> dict[str, Any]:
    values_by_document = {
        item["document_type"]: item["data_ledger"].get(topic, [])
        for item in documents
    }
    populated = {doc: values for doc, values in values_by_document.items() if values}
    if not documents:
        return {"status": "blocked", "summary": "No documents provided", "values_by_document": values_by_document, "blockers": ["empty_package"]}
    if topic in {"parties", "dates"} and len(populated) < len(documents):
        missing = sorted(set(values_by_document) - set(populated))
        return {
            "status": "review",
            "summary": f"Missing {topic} in {len(missing)} document(s)",
            "values_by_document": values_by_document,
            "blockers": [f"{topic} missing in {doc}" for doc in missing],
        }
    if topic == "parties" and len({tuple(values) for values in populated.values()}) > 1:
        return {
            "status": "review",
            "summary": "Parties differ across package documents",
            "values_by_document": values_by_document,
            "blockers": ["parties require cross-document confirmation"],
        }
    if topic in {"privacy_roles", "ip_ownership", "software_scope"} and not populated:
        return {
            "status": "review",
            "summary": f"No {topic} signals found",
            "values_by_document": values_by_document,
            "blockers": [f"{topic} needs specialist confirmation"],
        }
    return {
        "status": "passed" if populated else "review",
        "summary": f"{len(populated)} document(s) include {topic}",
        "values_by_document": values_by_document,
        "blockers": [],
    }


def _placeholder_check(documents: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = []
    for document in documents:
        for placeholder in document.get("placeholders", []):
            field = placeholder.get("field") if isinstance(placeholder, dict) else str(placeholder)
            taxonomy = placeholder.get("taxonomy", "") if isinstance(placeholder, dict) else ""
            blockers.append(f"{document['document_type']}: {field} {taxonomy}".strip())
    return {
        "status": "blocked" if blockers else "passed",
        "summary": f"{len(blockers)} placeholder(s)",
        "blockers": blockers,
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
