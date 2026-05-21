"""Paperclip payload builders for Hermes We Law OS."""

from __future__ import annotations

from typing import Any


APPROVAL_TYPES = {
    "aprobar_engagement_letter",
    "aprobar_documento",
    "aprobar_paquete_documentos",
    "aprobar_demanda_inicial",
    "aprobar_estrategia_litigio",
    "aprobar_revision_juridica",
    "confirmar_cierre_asunto",
    "confirmar_anticipo",
    "confirmar_cierre_financiero",
    "aprobar_actualizacion_plantilla",
}


def issue_payload(
    company_id: str,
    title: str,
    body: str,
    matter_id: str | None = None,
    assignee_agent_id: str | None = None,
) -> dict[str, Any]:
    data = {
        "title": title,
        "body": body,
        "status": "backlog",
        "priority": "medium",
    }
    if assignee_agent_id:
        data["assigneeAgentId"] = assignee_agent_id
    return envelope("issue", company_id, data, matter_id)


def task_payload(
    company_id: str,
    matter_id: str,
    title: str,
    owner: str,
    priority: str = "medium",
) -> dict[str, Any]:
    return envelope(
        "task",
        company_id,
        {
            "title": title,
            "body": f"Matter: {matter_id}\nOwner: {owner}",
            "status": "todo",
            "priority": priority,
        },
        matter_id,
    )


def comment_payload(company_id: str, issue_id: str, body: str, matter_id: str | None = None) -> dict[str, Any]:
    return envelope("comment", company_id, {"issueId": issue_id, "body": body}, matter_id)


def approval_payload(
    company_id: str,
    approval_type: str,
    title: str,
    summary: str,
    matter_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if approval_type not in APPROVAL_TYPES:
        raise ValueError(f"Unsupported approval type: {approval_type}")
    return envelope(
        "approval",
        company_id,
        {
            "type": approval_type,
            "title": title,
            "summary": summary,
            "payload": payload or {},
            "status": "pending",
        },
        matter_id,
    )


def envelope(kind: str, company_id: str, body: dict[str, Any], matter_id: str | None = None) -> dict[str, Any]:
    result = {"kind": kind, "company_id": company_id, "body": body}
    if matter_id:
        result["matter_id"] = matter_id
    return result
