"""Build and render the We Law live file."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from matter_events import replay_matter_events


@dataclass
class MissingData:
    para_avanzar: list[str] = field(default_factory=list)
    para_firma: list[str] = field(default_factory=list)
    no_bloqueantes: list[str] = field(default_factory=list)


def build_live_file(
    client: dict[str, Any],
    matter: dict[str, Any],
    documents: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    documents = documents or []
    tasks = tasks or []
    missing = classify_missing(client, matter, documents)

    existing_docs = [doc["title"] for doc in documents if doc.get("status") in {"borrador", "revision", "aprobado", "final"}]
    pending_docs = [doc["title"] for doc in documents if doc.get("status") in {"pendiente", "solicitado"}]

    return {
        "matter_id": matter.get("id", "MAT-PENDIENTE"),
        "client_id": client.get("id", "CLI-PENDIENTE"),
        "cliente": client.get("nombre", "Cliente pendiente"),
        "estado_asunto": matter.get("estado", "prospecto"),
        "fase_operativa": matter.get("fase", "consolidacion"),
        "docs_existentes": existing_docs,
        "docs_pendientes": pending_docs,
        "tareas_abiertas": [task["title"] for task in tasks if task.get("status") not in {"done", "cancelled"}],
        "faltantes_para_avanzar": missing.para_avanzar,
        "faltantes_para_firma": missing.para_firma,
        "faltantes_no_bloqueantes": missing.no_bloqueantes,
        "engagement": matter.get("engagement", "pendiente"),
        "workspace": workspace or matter.get("drive_path") or "pendiente",
    }


def build_live_file_from_events(
    matter_id: str,
    events: list[dict[str, Any]],
    *,
    workspace: str | None = None,
    current_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    replayed = replay_matter_events(events)
    if current_state:
        replayed["client"].update(current_state.get("client", {}))
        replayed["matter"].update(current_state.get("matter", {}))
        replayed["documents"].extend(current_state.get("documents", []))
        replayed["tasks"].extend(current_state.get("tasks", []))

    matter = {"id": matter_id, **replayed["matter"]}
    client = replayed["client"] or {"id": "CLI-PENDIENTE", "nombre": "Cliente pendiente"}
    live = build_live_file(
        client,
        matter,
        documents=replayed["documents"],
        tasks=replayed["tasks"],
        workspace=workspace,
    )
    live["eventos_recientes"] = list(reversed(replayed["recent_events"][-5:]))
    live["fuentes_indexadas"] = [item.get("name", item.get("path", "fuente")) for item in replayed["sources"]]
    live["plazos"] = [item.get("name", item.get("due_date", "plazo")) for item in replayed["deadlines"]]
    live["pagos"] = [item.get("amount", item.get("status", "pago")) for item in replayed["payments"]]
    live["aprobaciones"] = [item.get("type", item.get("status", "aprobacion")) for item in replayed["approvals"]]
    return live


def classify_missing(
    client: dict[str, Any],
    matter: dict[str, Any],
    documents: list[dict[str, Any]],
) -> MissingData:
    missing = MissingData()

    if not client.get("nombre"):
        missing.para_avanzar.append("cliente identificable")
    if not matter.get("descripcion"):
        missing.para_avanzar.append("descripcion del asunto")
    if not matter.get("tipo"):
        missing.para_avanzar.append("tipo de asunto")

    if not client.get("rfc"):
        missing.para_firma.append("RFC del cliente")
    if not client.get("domicilio"):
        missing.para_firma.append("domicilio del cliente")
    if matter.get("engagement") == "pendiente":
        missing.no_bloqueantes.append("engagement letter pendiente")

    requested_docs = {doc.get("type") for doc in documents}
    if matter.get("tipo", "").startswith("litigio") and "demanda_inicial" not in requested_docs:
        missing.no_bloqueantes.append("demanda inicial no solicitada todavia")

    return missing


def render_live_file(live_file: dict[str, Any]) -> str:
    def line_items(items: list[str]) -> str:
        return ", ".join(items) if items else "ninguno"

    lines = [
            "EXPEDIENTE VIVO",
            f"Matter: {live_file['matter_id']}",
            f"Cliente: {live_file['client_id']} / {live_file['cliente']}",
            f"Estado del asunto: {live_file['estado_asunto']}",
            f"Fase operativa: {live_file['fase_operativa']}",
            f"Docs existentes: {line_items(live_file['docs_existentes'])}",
            f"Docs pendientes: {line_items(live_file['docs_pendientes'])}",
            f"Tareas abiertas: {line_items(live_file['tareas_abiertas'])}",
            f"Faltantes para avanzar: {line_items(live_file['faltantes_para_avanzar'])}",
            f"Faltantes para firma: {line_items(live_file['faltantes_para_firma'])}",
            f"Faltantes no bloqueantes: {line_items(live_file['faltantes_no_bloqueantes'])}",
            f"Engagement: {live_file['engagement']}",
            f"Workspace: {live_file['workspace']}",
    ]
    if live_file.get("eventos_recientes"):
        lines.append(f"Eventos recientes: {line_items(live_file['eventos_recientes'])}")
    if live_file.get("plazos"):
        lines.append(f"Plazos: {line_items(live_file['plazos'])}")
    if live_file.get("aprobaciones"):
        lines.append(f"Aprobaciones: {line_items(live_file['aprobaciones'])}")
    return "\n".join(lines)
