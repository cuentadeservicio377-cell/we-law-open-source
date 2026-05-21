"""Build Paperclip context packages for Hermes We Law workers."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CORE_TOOLS = ROOT / "skills/hermes-welaw-core/tools"
DOC_TOOLS = ROOT / "skills/hermes-welaw-documentos/tools"
INTAKE_TOOLS = ROOT / "skills/hermes-welaw-intake/tools"
for tool_path in [CORE_TOOLS, DOC_TOOLS, INTAKE_TOOLS]:
    if str(tool_path) not in sys.path:
        sys.path.insert(0, str(tool_path))

from client_memory import ClientMemoryStore
from live_file import render_live_file
from template_registry import TemplateRegistry
from intake_sessions import IntakeSessionStore
from firm_command_spine import command_spine_summary
from google_workspace import build_workspace_topology_manifest
from legal_worker_contract import load_legal_worker_contract


def build_context_package(
    company_id: str,
    worker_role: str,
    client: dict[str, Any],
    matter: dict[str, Any],
    live_file: dict[str, Any],
    issue_id: str | None = None,
    command_record: dict[str, Any] | None = None,
    matter_brief: dict[str, Any] | None = None,
    delegation_plan: dict[str, Any] | None = None,
    role_assignment: dict[str, Any] | None = None,
    workspace_manifest: dict[str, Any] | None = None,
    approval_gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client_id = client["id"]
    memory_text = ClientMemoryStore().render_for_context(client_id, client.get("nombre", ""))
    template_context = TemplateRegistry().context_for_paperclip()
    intake_sessions = [
        item for item in IntakeSessionStore().list_open()
        if item.get("client_id") in {None, client_id} or item.get("matter_id") == matter.get("id")
    ]
    return {
        "kind": "paperclip_context_package",
        "company_id": company_id,
        "issue_id": issue_id,
        "worker_role": worker_role,
        "client_id": client_id,
        "matter_id": matter["id"],
        "firm_command_spine": command_spine_summary(),
        "legal_worker_contract": load_legal_worker_contract(),
        "command_record": command_record or fallback_command_record(client, matter),
        "matter_brief": matter_brief or fallback_matter_brief(client, matter),
        "delegation_plan": delegation_plan or fallback_delegation_plan(worker_role, matter),
        "role_assignment": role_assignment or fallback_role_assignment(worker_role, matter),
        "workspace_state": workspace_manifest or fallback_workspace_manifest(client, matter),
        "approval_gates": approval_gates or fallback_approval_gates(),
        "instructions": worker_instructions(worker_role),
        "expediente_vivo": render_live_file(live_file),
        "client_memory": memory_text,
        "templates": template_context,
        "intake_sessions": intake_sessions,
        "local_paths": {
            "client_root": client.get("drive_path", f"workspace/clientes/{client_id}"),
            "matter_root": matter.get("drive_path", f"workspace/matters/{matter['id']}"),
            "templates_root": "workspace/templates/legal",
        },
        "approval_policy": {
            "document_final_requires_approval": True,
            "template_update_requires_approval": True,
            "legal_filing_requires_approval": True,
        },
    }


def worker_instructions(worker_role: str) -> list[str]:
    base = [
        "Usa el EXPEDIENTE VIVO como fuente operativa.",
        "No inventes datos faltantes; marca placeholders.",
        "Devuelve resultado con cambios hechos, faltantes y siguiente aprobacion.",
    ]
    role_specific = {
        "documents": ["Selecciona template_id desde templates y reporta variables faltantes."],
        "intake": ["Completa intake_sessions antes de convertir a matter si faltan campos minimos."],
        "litigation": ["Separa hechos, pruebas, anexos, estrategia y plazos."],
        "deadlines": ["Crea tareas/plazos sin borrar vencimientos existentes."],
    }
    return base + role_specific.get(worker_role, [])


def fallback_command_record(client: dict[str, Any], matter: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "firm_command",
        "actor": "pablo",
        "controller": "hermes",
        "client_id": client["id"],
        "matter_id": matter["id"],
        "chain_of_command": ["pablo", "hermes", "paperclip_staff", "workspace", "dashboard"],
    }


def fallback_matter_brief(client: dict[str, Any], matter: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "matter_brief",
        "client_id": client["id"],
        "client_name": client.get("nombre", ""),
        "matter_id": matter["id"],
        "matter_type": matter.get("tipo", ""),
        "matter_description": matter.get("descripcion", ""),
    }


def fallback_delegation_plan(worker_role: str, matter: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "delegation_plan",
        "controller": "hermes",
        "staff_system": "paperclip",
        "matter_id": matter["id"],
        "assignments": [fallback_role_assignment(worker_role, matter)],
    }


def fallback_role_assignment(worker_role: str, matter: dict[str, Any]) -> dict[str, Any]:
    return {
        "order": 1,
        "role": worker_role,
        "title": f"Ejecutar rol {worker_role} - {matter['id']}",
        "required_artifacts": ["WORK_PRODUCT.md"],
        "depends_on": [],
    }


def fallback_workspace_manifest(client: dict[str, Any], matter: dict[str, Any]) -> dict[str, Any]:
    topology = build_workspace_topology_manifest(dry_run=True, approved=False)
    return {
        "kind": "matter_workspace_manifest",
        "office": topology,
        "client": {
            "id": client["id"],
            "name": client.get("nombre", ""),
            "root": client.get("drive_path", f"workspace/clientes/{client['id']}"),
        },
        "matter": {
            "id": matter["id"],
            "root": matter.get("drive_path", f"workspace/matters/{matter['id']}"),
        },
        "write_gate": topology["write_gate"],
    }


def fallback_approval_gates() -> list[dict[str, Any]]:
    return [
        {
            "type": "senior_review",
            "status": "required",
            "owner": "Revisor Senior",
            "reason": "Todo entregable legal requiere revision senior.",
        }
    ]


def assert_json_serializable(package: dict[str, Any]) -> None:
    json.dumps(package, ensure_ascii=False)
