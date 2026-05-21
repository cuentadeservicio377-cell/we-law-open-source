"""Local Google Sheets control-master fallback for Hermes We Law OS."""

from __future__ import annotations

from datetime import datetime
from typing import Any


CONTROL_TABLES = [
    "Clientes",
    "Matters",
    "Fuentes",
    "Transcripciones",
    "Hechos",
    "Documentos",
    "Faltantes",
    "Correcciones",
    "Tareas",
    "Aprobaciones",
    "Plazos",
    "Cobranza",
    "Entregables",
]


def build_control_master_update(context: dict[str, Any]) -> dict[str, Any]:
    client = context.get("client", {})
    matter = context.get("matter", {})
    transcript_intake = context.get("transcript_intake", {})
    sources = list(context.get("sources", []))

    tables = empty_tables()
    tables["Clientes"].append(client_row(client))
    tables["Matters"].append(matter_row(client, matter))
    tables["Fuentes"].extend(source_rows(matter, sources))
    tables["Transcripciones"].extend(transcript_rows(matter, sources))
    tables["Hechos"].extend(fact_rows(client, matter, transcript_intake.get("data_ledger", {})))
    tables["Documentos"].extend(document_rows(matter, transcript_intake.get("required_documents", [])))
    tables["Faltantes"].extend(missing_rows(client, matter, transcript_intake.get("missing_info", [])))
    tables["Correcciones"].extend(correction_rows(matter, transcript_intake.get("corrections", [])))
    tables["Tareas"].extend(simple_rows("task", matter, context.get("tasks", [])))
    tables["Aprobaciones"].extend(simple_rows("approval", matter, context.get("approvals", [])))
    tables["Plazos"].extend(simple_rows("deadline", matter, context.get("deadlines", [])))
    tables["Cobranza"].extend(simple_rows("billing", matter, context.get("billing", [])))
    tables["Entregables"].extend(simple_rows("deliverable", matter, context.get("deliverables", [])))

    return {
        "kind": "control_master_update",
        "mode": "local_fallback",
        "generated_at": now(),
        "live_google_sheets_write": False,
        "requires_approval_for_live_write": True,
        "tables": tables,
    }


def empty_tables() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in CONTROL_TABLES}


def client_row(client: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client.get("id", ""),
        "client_name": client.get("nombre") or client.get("name", ""),
        "rfc": client.get("rfc", ""),
        "status": client.get("estado", client.get("status", "activo")),
    }


def matter_row(client: dict[str, Any], matter: dict[str, Any]) -> dict[str, Any]:
    return {
        "matter_id": matter.get("id", ""),
        "client_id": matter.get("client_id", client.get("id", "")),
        "client_name": matter.get("cliente") or client.get("nombre") or client.get("name", ""),
        "matter_type": matter.get("tipo") or matter.get("type", ""),
        "description": matter.get("descripcion") or matter.get("description", ""),
        "status": matter.get("estado", matter.get("status", "prospecto")),
    }


def source_rows(matter: dict[str, Any], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": item.get("id", ""),
            "matter_id": matter.get("id", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source_type": item.get("type", "transcript"),
        }
        for item in sources
    ]


def transcript_rows(matter: dict[str, Any], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "transcript_id": item.get("id", ""),
            "matter_id": matter.get("id", ""),
            "title": item.get("title", ""),
            "status": "indexed",
        }
        for item in sources
        if item.get("type", "transcript") == "transcript"
    ]


def fact_rows(client: dict[str, Any], matter: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "matter_id": matter.get("id", ""),
            "client_id": client.get("id", ""),
            "field": field,
            "value": fact.get("value", ""),
            "source_id": fact.get("source_id", ""),
            "confidence": fact.get("confidence", ""),
        }
        for field, fact in ledger.items()
    ]


def document_rows(matter: dict[str, Any], document_types: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "matter_id": matter.get("id", ""),
            "document_type": document_type,
            "status": "requested",
            "source": "legal_knowledge_map",
        }
        for document_type in document_types
    ]


def missing_rows(client: dict[str, Any], matter: dict[str, Any], missing_info: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "matter_id": matter.get("id", ""),
            "client_id": client.get("id", ""),
            "field": item.get("field", ""),
            "taxonomy": item.get("taxonomy", ""),
            "reason": item.get("reason", ""),
            "status": "open",
        }
        for item in missing_info
    ]


def correction_rows(matter: dict[str, Any], corrections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "matter_id": matter.get("id", ""),
            "target": item.get("target", ""),
            "instruction": item.get("instruction", ""),
            "source_id": item.get("source_id", ""),
            "status": item.get("status", "pending_application"),
        }
        for item in corrections
    ]


def simple_rows(kind: str, matter: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        item.setdefault("matter_id", matter.get("id", ""))
        item.setdefault("kind", kind)
        normalized.append(item)
    return normalized


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")

