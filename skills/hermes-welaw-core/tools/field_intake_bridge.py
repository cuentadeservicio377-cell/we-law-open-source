"""Telegram-style field intake bridge for Hermes We Law OS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[3]
INTAKE_TOOLS = ROOT / "skills/hermes-welaw-intake/tools"
EXPEDIENTES_TOOLS = ROOT / "skills/hermes-welaw-expedientes/tools"
PAPERCLIP_TOOLS = ROOT / "skills/hermes-welaw-paperclip/tools"
for tool_path in [INTAKE_TOOLS, EXPEDIENTES_TOOLS, PAPERCLIP_TOOLS]:
    if str(tool_path) not in sys.path:
        sys.path.insert(0, str(tool_path))

from client_memory import ClientMemoryStore
from intake import Intake, next_id
from intake_sessions import IntakeSessionStore
from folder_planner import plan_client_matter_folders
from live_file import build_live_file, render_live_file
from context_package import build_context_package, assert_json_serializable
from trigger_catalog import normalize_telegram_note
from matter_events import MatterEventStore
from legal_knowledge import infer_required_documents
from google_workspace import MATTER_FOLDER_TEMPLATE, build_workspace_topology_manifest


DOCUMENT_LABELS = {
    "contrato_prestacion": "Contrato de prestacion de servicios",
    "nda": "NDA",
    "demanda_inicial": "Demanda inicial",
    "memo_estrategia": "Memo de estrategia",
    "aviso_privacidad": "Aviso de privacidad",
}


@dataclass(frozen=True)
class BridgePaths:
    clients: Path = ROOT / "data/clients.json"
    matters: Path = ROOT / "data/matters.json"
    documents: Path = ROOT / "data/documents.json"
    tasks: Path = ROOT / "data/tasks.json"
    inbox: Path = ROOT / "workspace/inbox"
    generated: Path = ROOT / "workspace/generated"
    memory_root: Path = ROOT / "data/client_memory"
    intake_sessions: Path = ROOT / "data/intake_sessions.json"
    matter_events: Path = ROOT / "data/matter_events"
    manifest: Path = ROOT / "runtime/config/paperclip-welaw-instance.json"


class PaperclipBridgeError(RuntimeError):
    """Raised when live Paperclip issue creation fails."""


def build_field_intake(
    message: str,
    *,
    source: str = "telegram",
    paths: BridgePaths = BridgePaths(),
    apply_local: bool = False,
) -> dict[str, Any]:
    """Convert a lawyer field note into durable We Law operating context."""

    parsed = parse_field_message(message)
    legal_trigger = normalize_telegram_note(message)
    clients = load_json(paths.clients, [])
    matters = load_json(paths.matters, [])
    documents = load_json(paths.documents, [])
    tasks = load_json(paths.tasks, [])
    manifest = load_json(paths.manifest, {})

    intake_result = Intake(clients, matters).open_or_reuse(
        nombre=parsed["client_name"],
        descripcion=parsed["matter_description"],
        tipo=parsed["matter_type"],
        rfc=parsed.get("client_rfc"),
        engagement="pendiente",
    )
    client = dict(intake_result.client)
    matter = dict(intake_result.matter)
    matter["fase"] = next_phase(parsed["requested_documents"], parsed["matter_type"])
    if matter.get("estado") == "prospecto" and parsed["requested_documents"]:
        matter["estado"] = "activo"

    folder_plan = plan_client_matter_folders(client, matter)
    client["drive_path"] = folder_plan["client_root"]
    matter["drive_path"] = folder_plan["matter_root"]

    doc_records = planned_documents(documents, matter, parsed["requested_documents"])
    task_records = planned_tasks(tasks, matter, parsed["requested_documents"])
    all_documents = upsert_preview(documents, doc_records, key_fields=("matter_id", "type", "title"))
    all_tasks = upsert_preview(tasks, task_records, key_fields=("matter_id", "title", "owner"))

    live_file = build_live_file(
        client,
        matter,
        documents=[doc for doc in all_documents if doc.get("matter_id") == matter["id"]],
        tasks=[task for task in all_tasks if task.get("matter_id") == matter["id"]],
        workspace=folder_plan["matter_root"],
    )

    memory_store = ClientMemoryStore(paths.memory_root)
    memory = memory_store.add(
        client["id"],
        client.get("nombre", ""),
        facts=[f"Nota de campo por {source}: {message.strip()}"],
        preferences=[],
        risks=parsed["risks"],
        matter_id=matter["id"],
        document_note=document_note(parsed["requested_documents"]),
        event="field_intake",
        summary=f"{source} intake convertido a contexto operativo para {matter['id']}",
    ) if apply_local else memory_store.load(client["id"], client.get("nombre", ""))

    intake_store = IntakeSessionStore(paths.intake_sessions)
    intake_session = intake_store.create(
        {
            "client_id": client["id"],
            "matter_id": matter["id"],
            "client_name": client["nombre"],
            "matter_description": matter["descripcion"],
            "matter_type": matter["tipo"],
            "client_rfc": client.get("rfc"),
        },
        source=source,
    ).session if apply_local else preview_intake_session(client, matter, source)

    context_package = build_context_package(
        manifest.get("companyId", ""),
        "master",
        client,
        matter,
        live_file,
    )
    assert_json_serializable(context_package)
    command_record = build_command_record(message, source, client, matter, parsed, legal_trigger)
    matter_brief = build_matter_brief(client, matter, parsed, live_file, memory, intake_session)
    workspace_manifest = build_matter_workspace_manifest(client, matter, folder_plan)
    approval_gates = build_approval_gates(parsed, matter)
    delegation_plan = build_delegation_plan(parsed, matter, doc_records, task_records, approval_gates)
    partner_briefing = build_partner_briefing(client, matter, delegation_plan, approval_gates)

    result = {
        "kind": "field_intake_bridge",
        "source": source,
        "received_at": now(),
        "message": message,
        "parsed": parsed,
        "legal_trigger": legal_trigger,
        "client": client,
        "matter": matter,
        "client_status": intake_result.client_status,
        "matter_status": intake_result.matter_status,
        "intake_session": intake_session,
        "folder_plan": folder_plan,
        "live_file": live_file,
        "rendered_live_file": render_live_file(live_file),
        "client_memory": memory,
        "command_record": command_record,
        "matter_brief": matter_brief,
        "delegation_plan": delegation_plan,
        "workspace_manifest": workspace_manifest,
        "approval_gates": approval_gates,
        "partner_briefing": partner_briefing,
        "planned_documents": doc_records,
        "planned_tasks": task_records,
        "context_package": context_package,
        "paperclip_issue_requests": build_paperclip_issue_requests(
            manifest,
            message,
            client,
            matter,
            live_file,
            doc_records,
            task_records,
            command_record,
            matter_brief,
            delegation_plan,
            workspace_manifest,
            approval_gates,
        ),
    }

    if apply_local:
        result["matter_event"] = MatterEventStore(paths.matter_events).append(
            matter["id"],
            "intake",
            {
                "client": client,
                "matter": matter,
                "intake_session_id": intake_session["id"],
                "collected": intake_session.get("collected", {}),
                "missing_by_urgency": intake_session.get("missing_by_urgency", {}),
                "legal_trigger": legal_trigger,
                "command_record": command_record,
                "delegation_plan": delegation_plan,
                "workspace_manifest": workspace_manifest,
                "approval_gates": approval_gates,
            },
            actor="Recepcionista Juridico",
            source=source,
        )
        persist_local(paths, result, clients, matters, documents, tasks, client, matter, doc_records, task_records)

    return result


def parse_field_message(message: str) -> dict[str, Any]:
    normalized = normalize(message)
    requested_documents = infer_documents(normalized)
    matter_type = infer_matter_type(normalized)
    client_name = extract_client_name(message) or "Cliente por confirmar"
    matter_description = infer_matter_description(normalized, requested_documents, matter_type)
    risks = []
    if "firma" in normalized or requested_documents:
        risks.append("Faltan datos de firma si no estan en expediente: RFC, domicilio y representante.")
    return {
        "client_name": client_name,
        "matter_description": matter_description,
        "matter_type": matter_type,
        "requested_documents": requested_documents,
        "risks": risks,
        "confidence": 0.86 if client_name != "Cliente por confirmar" else 0.55,
    }


def extract_client_name(message: str) -> str | None:
    patterns = [
        r"(?:fui a ver a|vi a|me reuni con|reunión con|reunion con)\s+(.+?)(?:[.,;]| quiere\b| necesita\b| me pid[ií]o\b| pide\b| solicita\b| para\b|$)",
        r"(?:cliente|prospecto)\s+(.+?)(?:[.,;]| quiere\b| necesita\b| me pid[ií]o\b| pide\b| solicita\b| para\b|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).strip().split())
            return value.strip(" .,:;") or None
    return None


def infer_documents(normalized: str) -> list[str]:
    docs: list[str] = []
    if "contrato" in normalized or "prestacion de servicios" in normalized:
        docs.append("contrato_prestacion")
    if "nda" in normalized or "confidencialidad" in normalized:
        docs.append("nda")
    if "demanda" in normalized:
        docs.append("demanda_inicial")
    if "estrategia" in normalized:
        docs.append("memo_estrategia")
    if "aviso de privacidad" in normalized:
        docs.append("aviso_privacidad")
    for doc_type in infer_required_documents(normalized):
        if doc_type not in docs:
            docs.append(doc_type)
    return docs or ["memo_estrategia"]


def infer_matter_type(normalized: str) -> str:
    if any(token in normalized for token in ["demanda", "juicio", "juzgado", "audiencia", "litigio"]):
        return "litigio_civil"
    if any(token in normalized for token in ["compliance", "cumplimiento"]):
        return "compliance"
    if any(token in normalized for token in ["sociedad", "asamblea", "corporativo"]):
        return "corporativo"
    return "contractual"


def infer_matter_description(normalized: str, documents: list[str], matter_type: str) -> str:
    if matter_type.startswith("litigio"):
        return "Asunto litigioso reportado desde campo"
    labels = [DOCUMENT_LABELS.get(doc, doc) for doc in documents]
    return "Paquete documental: " + " y ".join(labels)


def planned_documents(existing: list[dict[str, Any]], matter: dict[str, Any], requested_documents: list[str]) -> list[dict[str, Any]]:
    ids = [item["id"] for item in existing if item.get("id")]
    planned = []
    next_doc_id = next_id("DOC", ids)
    next_num = int(next_doc_id.split("-", 1)[1])
    for offset, doc_type in enumerate(requested_documents):
        title = f"{DOCUMENT_LABELS.get(doc_type, doc_type)} {matter['cliente']} v1"
        planned.append(
            {
                "id": f"DOC-{next_num + offset:03d}",
                "matter_id": matter["id"],
                "type": doc_type,
                "title": title,
                "status": "borrador",
                "version": "v1",
                "drive_path": f"{matter['drive_path']}/02-Documentos en trabajo/{title}.md",
            }
        )
    return planned


def planned_tasks(existing: list[dict[str, Any]], matter: dict[str, Any], requested_documents: list[str]) -> list[dict[str, Any]]:
    ids = [item["id"] for item in existing if item.get("id")]
    next_task_id = next_id("TRA", ids)
    next_num = int(next_task_id.split("-", 1)[1])
    tasks = [
        {
            "id": f"TRA-{next_num:03d}",
            "matter_id": matter["id"],
            "title": "Validar intake y faltantes de firma",
            "status": "todo",
            "owner": "Recepcionista Juridico",
            "priority": "high",
        }
    ]
    for offset, doc_type in enumerate(requested_documents, start=1):
        tasks.append(
            {
                "id": f"TRA-{next_num + offset:03d}",
                "matter_id": matter["id"],
                "title": f"Preparar {DOCUMENT_LABELS.get(doc_type, doc_type)}",
                "status": "todo",
                "owner": "Documentos Legales",
                "priority": "high",
            }
        )
    tasks.append(
        {
            "id": f"TRA-{next_num + len(requested_documents) + 1:03d}",
            "matter_id": matter["id"],
            "title": "Dar seguimiento a aprobacion y firma",
            "status": "todo",
            "owner": "Plazos",
            "priority": "medium",
        }
    )
    return tasks


def build_command_record(
    message: str,
    source: str,
    client: dict[str, Any],
    matter: dict[str, Any],
    parsed: dict[str, Any],
    legal_trigger: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"CMD-{matter['id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "kind": "firm_command",
        "source": source,
        "actor": "pablo",
        "controller": "hermes",
        "received_at": now(),
        "original_instruction": message,
        "client_id": client["id"],
        "matter_id": matter["id"],
        "intent": legal_trigger.get("intent", parsed.get("matter_type", "seguimiento")),
        "confidence": parsed.get("confidence", 0),
        "chain_of_command": ["pablo", "hermes", "paperclip_staff", "workspace", "dashboard"],
        "operating_rule": "Hermes dirige; Paperclip ejecuta; Workspace conserva; the lawyer aprueba.",
    }


def build_matter_brief(
    client: dict[str, Any],
    matter: dict[str, Any],
    parsed: dict[str, Any],
    live_file: dict[str, Any],
    memory: dict[str, Any] | str,
    intake_session: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "matter_brief",
        "client_id": client["id"],
        "client_name": client.get("nombre", ""),
        "matter_id": matter["id"],
        "matter_type": matter.get("tipo", ""),
        "matter_description": matter.get("descripcion", ""),
        "requested_documents": parsed.get("requested_documents", []),
        "risks": parsed.get("risks", []),
        "live_file_status": live_file.get("estado", live_file.get("status", "active")),
        "memory_available": bool(memory),
        "intake_session_id": intake_session.get("id"),
    }


def build_matter_workspace_manifest(
    client: dict[str, Any],
    matter: dict[str, Any],
    folder_plan: dict[str, Any],
) -> dict[str, Any]:
    topology = build_workspace_topology_manifest(dry_run=True, approved=False)
    return {
        "kind": "matter_workspace_manifest",
        "office": topology,
        "client": {
            "id": client["id"],
            "name": client.get("nombre", ""),
            "root": folder_plan["client_root"],
        },
        "matter": {
            "id": matter["id"],
            "root": folder_plan["matter_root"],
            "folder_template": MATTER_FOLDER_TEMPLATE,
        },
        "write_gate": topology["write_gate"],
    }


def build_approval_gates(parsed: dict[str, Any], matter: dict[str, Any]) -> list[dict[str, Any]]:
    gates = [
        {
            "type": "senior_review",
            "status": "required",
            "owner": "Revisor Senior",
            "reason": "Todo entregable legal requiere revision senior antes de enviarse al cliente.",
        },
        {
            "type": "client_delivery",
            "status": "blocked_until_review",
            "owner": "Hermes Managing Partner",
            "reason": "Hermes solo puede reportar como entregable despues de revisar artefactos y faltantes.",
        },
        {
            "type": "workspace_writeback",
            "status": "dry_run",
            "owner": "Hermes Managing Partner",
            "reason": "La escritura viva en Workspace requiere credenciales sanas y aprobacion explicita.",
        },
    ]
    if parsed.get("requested_documents"):
        gates.append(
            {
                "type": "signature",
                "status": "blocked_until_missing_info_closed",
                "owner": "the lawyer / Socio dueno",
                "reason": "Los documentos de firma requieren datos de firma completos o placeholders clasificados.",
            }
        )
    if str(matter.get("tipo", "")).startswith("litigio"):
        gates.append(
            {
                "type": "legal_filing",
                "status": "blocked_until_express_approval",
                "owner": "the lawyer / Socio dueno",
                "reason": "Ningun escrito se presenta sin autorizacion expresa.",
            }
        )
    return gates


def build_delegation_plan(
    parsed: dict[str, Any],
    matter: dict[str, Any],
    documents: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    approval_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    roles = ["master", "intake", "file", "sheets", "legal_research"]
    requested_docs = set(parsed.get("requested_documents", []))
    if documents:
        roles.append("documents")
    if requested_docs.intersection({"aviso_privacidad", "aviso_privacidad_integral", "aviso_privacidad_medicos_pacientes", "formato_arco"}):
        roles.append("privacy")
    if requested_docs.intersection({"nda", "contrato_desarrollo_software", "convenio_cotitularidad"}) or "software" in str(matter.get("descripcion", "")).lower():
        roles.append("ip_software")
    if str(matter.get("tipo", "")).startswith("litigio"):
        roles.append("litigation")
    roles.extend(["deadlines", "editorial", "senior_review"])
    if any("pago" in str(task.get("title", "")).lower() or "honorario" in str(task.get("title", "")).lower() for task in tasks):
        roles.append("collections")
    roles.append("admin")
    ordered_roles = dedupe(roles)
    assignments = [
        {
            "order": index + 1,
            "role": role,
            "title": assignment_title(role, matter),
            "required_artifacts": required_artifacts_for_role(role),
            "depends_on": [] if index == 0 else [ordered_roles[index - 1]],
        }
        for index, role in enumerate(ordered_roles)
    ]
    return {
        "kind": "delegation_plan",
        "matter_id": matter["id"],
        "controller": "hermes",
        "staff_system": "paperclip",
        "assignments": assignments,
        "approval_gate_types": [gate["type"] for gate in approval_gates],
    }


def build_partner_briefing(
    client: dict[str, Any],
    matter: dict[str, Any],
    delegation_plan: dict[str, Any],
    approval_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": "partner_briefing",
        "audience": "pablo",
        "channel": "telegram_or_dashboard",
        "summary": f"Hermes abrio {matter['id']} para {client.get('nombre', '')} y activo {len(delegation_plan['assignments'])} puestos del despacho.",
        "next_ask": "Revisar faltantes de firma y aprobar entregables cuando Revisor Senior libere el paquete.",
        "approval_gates": [gate["type"] for gate in approval_gates],
    }


def required_artifacts_for_role(role: str) -> list[str]:
    artifacts = {
        "master": ["MATTER_STATUS.md", "ROUTING_DECISION.json", "DECISION_LOG.md"],
        "intake": ["INTAKE_SUMMARY.md", "MISSING_INFO.json"],
        "file": ["EXPEDIENTE_VIVO.md", "FOLDER_MANIFEST.json", "SOURCE_INDEX.md"],
        "sheets": ["SHEETS_UPDATE_PLAN.json", "CLIENT_ROW.json", "MATTER_ROW.json"],
        "legal_research": ["LEGAL_BASIS_MEMO.md", "DOCUMENT_REQUIREMENTS.json", "RISK_MATRIX.md"],
        "documents": ["EVIDENCE_MAP.md", "DATA_LEDGER.json", "DELIVERABLE_MANIFEST.json", "LEGAL_QA.md"],
        "privacy": ["PRIVACY_DATA_MAP.json", "COMPLIANCE_MATRIX.md", "PRIVACY_QA.md"],
        "ip_software": ["IP_OWNERSHIP_MATRIX.md", "SOFTWARE_SCOPE_LEDGER.json", "TECH_CONTRACT_QA.md"],
        "litigation": ["CASE_THEORY.md", "PROCEDURAL_POSTURE.md", "EVIDENCE_TABLE.md"],
        "deadlines": ["DEADLINE_LEDGER.json", "CALENDAR_SYNC_PLAN.md"],
        "collections": ["BILLING_LEDGER.json", "WORK_AUTHORIZATION_STATUS.md"],
        "editorial": ["EDITORIAL_SPEC.json", "RENDER_MANIFEST.json", "VISUAL_QA.md"],
        "senior_review": ["SENIOR_REVIEW.md", "LEGAL_RISK_MEMO.md", "CLIENT_DELIVERY_DECISION.md"],
        "admin": ["LESSONS_LEARNED.md", "KNOWLEDGE_INDEX.json"],
    }
    return artifacts.get(role, ["WORK_PRODUCT.md"])


def assignment_title(role: str, matter: dict[str, Any]) -> str:
    labels = {
        "master": "Dirigir asunto y reportar a the lawyer",
        "intake": "Validar intake y faltantes",
        "file": "Armar expediente vivo",
        "sheets": "Actualizar control maestro",
        "legal_research": "Determinar base juridica y riesgos",
        "documents": "Redactar documentos legales",
        "privacy": "Revisar privacidad y compliance",
        "ip_software": "Revisar tecnologia, software e IP",
        "litigation": "Preparar estrategia litigiosa",
        "deadlines": "Controlar plazos y recordatorios",
        "collections": "Controlar cobranza y autorizacion de trabajo",
        "editorial": "Preparar version editorial para cliente",
        "senior_review": "Revisar y aprobar paquete",
        "admin": "Capturar lecciones y biblioteca",
    }
    return f"{labels.get(role, role)} - {matter['id']}"


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def build_paperclip_issue_requests(
    manifest: dict[str, Any],
    message: str,
    client: dict[str, Any],
    matter: dict[str, Any],
    live_file: dict[str, Any],
    documents: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    command_record: dict[str, Any] | None = None,
    matter_brief: dict[str, Any] | None = None,
    delegation_plan: dict[str, Any] | None = None,
    workspace_manifest: dict[str, Any] | None = None,
    approval_gates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    agents = manifest.get("agents", {})
    company_id = manifest.get("companyId", "")
    assignments = {item["role"]: item for item in (delegation_plan or {}).get("assignments", [])}
    parent_body = "\n\n".join(
        [
            "Cadena de mando: the lawyer instruye; Hermes Managing Partner dirige; Paperclip staff ejecuta; Workspace conserva; the lawyer aprueba.",
            "Entrada desde Telegram/campo.",
            f"Mensaje original: {message}",
            render_live_file(live_file),
            "Accion requerida: coordinar workers Hermes, mantener expediente vivo y reportar faltantes.",
        ]
    )
    requests = [
        {
            "role": "master",
            "company_id": company_id,
            "title": f"Telegram intake: {client['nombre']} / {matter['id']}",
            "description": parent_body,
            "priority": "high",
            "assigneeAgentId": agents.get("master"),
            "context_package": build_context_package(
                company_id,
                "master",
                client,
                matter,
                live_file,
                command_record=command_record,
                matter_brief=matter_brief,
                delegation_plan=delegation_plan,
                role_assignment=assignments.get("master"),
                workspace_manifest=workspace_manifest,
                approval_gates=approval_gates,
            ),
        }
    ]
    task_requests = []
    for task in tasks:
        role = role_for_owner(task.get("owner", ""))
        description = "\n\n".join(
            [
                "Hermes Managing Partner asigna esta tarea a Paperclip staff.",
                "La ejecucion debe respetar el paquete de contexto y los gates de aprobacion.",
                f"Matter: {matter['id']}\nCliente: {client['nombre']}",
                render_live_file(live_file),
            ]
        )
        task_requests.append(
            {
                "role": role,
            "company_id": company_id,
            "title": task["title"],
                "description": description,
            "priority": task.get("priority", "medium"),
                "assigneeAgentId": agents.get(role),
            "matter_id": matter["id"],
                "context_package": build_context_package(
                    company_id,
                    role,
                    client,
                    matter,
                    live_file,
                    command_record=command_record,
                    matter_brief=matter_brief,
                    delegation_plan=delegation_plan,
                    role_assignment=assignments.get(role),
                    workspace_manifest=workspace_manifest,
                    approval_gates=approval_gates,
                ),
        }
        )
    requests.extend(task_requests)
    has_document_task = any(request_item["role"] == "documents" for request_item in task_requests)
    if documents and not has_document_task:
        description = "\n".join(
            [
                "Hermes Managing Partner asigna paquete documental a Paperclip staff.",
                "No reducir documentos legales; preservar sustancia, fuentes, placeholders y revision senior.",
                "Documentos solicitados:",
                *[f"- {doc['title']}" for doc in documents],
            ]
        )
        requests.append(
            {
                "role": "documents",
                "company_id": company_id,
                "title": f"Preparar paquete documental {matter['id']}",
                "description": description,
                "priority": "high",
                "assigneeAgentId": agents.get("documents"),
                "matter_id": matter["id"],
                "context_package": build_context_package(
                    company_id,
                    "documents",
                    client,
                    matter,
                    live_file,
                    command_record=command_record,
                    matter_brief=matter_brief,
                    delegation_plan=delegation_plan,
                    role_assignment=assignments.get("documents"),
                    workspace_manifest=workspace_manifest,
                    approval_gates=approval_gates,
                ),
            }
        )
    elif documents and has_document_task:
        for request_item in requests:
            if request_item["role"] != "documents":
                continue
            request_item["description"] = "\n".join(
                [
                    request_item["description"],
                    "",
                    "Paquete documental relacionado:",
                    *[f"- {doc['title']}" for doc in documents],
                    "No crear una version reducida ni cerrar sin matriz de evidencia, placeholders y QA.",
                ]
            )
    existing_roles = {request_item["role"] for request_item in requests}
    for assignment in (delegation_plan or {}).get("assignments", []):
        role = assignment["role"]
        if role in existing_roles:
            continue
        description = "\n\n".join(
            [
                "Hermes Managing Partner abre este frente para Paperclip staff.",
                "Este issue existe para que la firma opere completa, no como tarea aislada.",
                f"Rol: {role}",
                f"Matter: {matter['id']}",
                f"Cliente: {client['nombre']}",
                "Artefactos requeridos:",
                *[f"- {artifact}" for artifact in assignment.get("required_artifacts", [])],
            ]
        )
        requests.append(
            {
                "role": role,
                "company_id": company_id,
                "title": assignment.get("title", f"Ejecutar {role} - {matter['id']}"),
                "description": description,
                "priority": "high" if role in {"file", "sheets", "legal_research", "senior_review"} else "medium",
                "assigneeAgentId": agents.get(role),
                "matter_id": matter["id"],
                "context_package": build_context_package(
                    company_id,
                    role,
                    client,
                    matter,
                    live_file,
                    command_record=command_record,
                    matter_brief=matter_brief,
                    delegation_plan=delegation_plan,
                    role_assignment=assignment,
                    workspace_manifest=workspace_manifest,
                    approval_gates=approval_gates,
                ),
            }
        )
        existing_roles.add(role)
    return requests


def apply_paperclip_issues(result: dict[str, Any], api_url: str | None = None) -> list[dict[str, Any]]:
    manifest = load_json(BridgePaths().manifest, {})
    api = (api_url or manifest.get("apiUrl") or "http://127.0.0.1:3100/api").rstrip("/")
    created = []
    parent_id: str | None = None
    for index, issue in enumerate(result["paperclip_issue_requests"]):
        body = {
            "title": issue["title"],
            "description": issue["description"],
            "status": "todo",
            "priority": issue.get("priority", "medium"),
        }
        if issue.get("assigneeAgentId"):
            body["assigneeAgentId"] = issue["assigneeAgentId"]
        if parent_id and index > 0:
            body["parentId"] = parent_id
        response = request_json("POST", f"{api}/companies/{issue['company_id']}/issues", body)
        if index == 0:
            parent_id = response.get("id")
        created.append({"role": issue["role"], "issue": response})
    return created


def request_json(method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        raise PaperclipBridgeError(f"{method} {url} -> HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except error.URLError as exc:
        raise PaperclipBridgeError(f"{method} {url} -> {exc.reason}") from exc


def persist_local(
    paths: BridgePaths,
    result: dict[str, Any],
    clients: list[dict[str, Any]],
    matters: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    client: dict[str, Any],
    matter: dict[str, Any],
    doc_records: list[dict[str, Any]],
    task_records: list[dict[str, Any]],
) -> None:
    save_json(paths.clients, upsert_preview(clients, [client], key_fields=("id",)))
    save_json(paths.matters, upsert_preview(matters, [matter], key_fields=("id",)))
    save_json(paths.documents, upsert_preview(documents, doc_records, key_fields=("matter_id", "type", "title")))
    save_json(paths.tasks, upsert_preview(tasks, task_records, key_fields=("matter_id", "title", "owner")))
    paths.inbox.mkdir(parents=True, exist_ok=True)
    paths.generated.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_matter = matter["id"].lower()
    save_json(paths.inbox / f"{stamp}-{safe_matter}-telegram.json", result)
    (paths.generated / f"{safe_matter}-expediente-vivo.md").write_text(
        result["rendered_live_file"] + "\n",
        encoding="utf-8",
    )
    save_json(paths.generated / f"{safe_matter}-context-package.json", result["context_package"])


def preview_intake_session(client: dict[str, Any], matter: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "id": "INTAKE-PREVIEW",
        "status": "ready_for_matter",
        "source": source,
        "client_id": client["id"],
        "matter_id": matter["id"],
        "collected": {
            "client_name": client["nombre"],
            "matter_description": matter["descripcion"],
            "matter_type": matter["tipo"],
        },
        "missing": ["client_rfc", "client_address", "signer_name"],
        "next_questions": [
            "¿Cuál es el RFC del cliente?",
            "¿Cuál es el domicilio para firma?",
            "¿Quién firmará por el cliente?",
        ],
        "history": [{"event": "preview", "timestamp": now(), "summary": "preview only; not persisted"}],
    }


def upsert_preview(existing: list[dict[str, Any]], new_items: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    result = [dict(item) for item in existing]
    for item in new_items:
        key = tuple(item.get(field) for field in key_fields)
        index = next((i for i, current in enumerate(result) if tuple(current.get(field) for field in key_fields) == key), None)
        if index is None:
            result.append(dict(item))
        else:
            result[index] = {**result[index], **item}
    return result


def role_for_owner(owner: str) -> str:
    value = normalize(owner)
    if "recepcionista" in value or "intake" in value:
        return "intake"
    if "expediente" in value or "records" in value or "file" in value:
        return "file"
    if "sheets" in value or "data clerk" in value or "google sheets" in value:
        return "sheets"
    if "analista" in value or "juridico" in value or "research" in value:
        return "legal_research"
    if "document" in value:
        return "documents"
    if "privacidad" in value or "compliance" in value:
        return "privacy"
    if "software" in value or "ip" in value:
        return "ip_software"
    if "litigio" in value:
        return "litigation"
    if "plazo" in value:
        return "deadlines"
    if "cobranza" in value:
        return "collections"
    if "editorial" in value or "produccion" in value:
        return "editorial"
    if "senior" in value or "revisor" in value:
        return "senior_review"
    if "admin" in value or "biblioteca" in value:
        return "admin"
    return "master"


def next_phase(documents: list[str], matter_type: str) -> str:
    if matter_type.startswith("litigio"):
        return "preparacion_litigio"
    if documents:
        return "generacion_documental"
    return "intake"


def document_note(documents: list[str]) -> str:
    labels = [DOCUMENT_LABELS.get(item, item) for item in documents]
    return "Documentos solicitados desde campo: " + ", ".join(labels)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(value: str) -> str:
    text = value.lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
