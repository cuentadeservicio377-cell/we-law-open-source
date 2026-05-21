"""Hermes intake orchestrator for Drive migrations and new-client conversations."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CORE_TOOLS = ROOT / "skills/hermes-welaw-core/tools"
EXPEDIENTES_TOOLS = ROOT / "skills/hermes-welaw-expedientes/tools"
PAPERCLIP_TOOLS = ROOT / "skills/hermes-welaw-paperclip/tools"
for tool_path in [Path(__file__).resolve().parent, CORE_TOOLS, EXPEDIENTES_TOOLS, PAPERCLIP_TOOLS]:
    if str(tool_path) not in sys.path:
        sys.path.insert(0, str(tool_path))

from transcript_intake import build_transcript_intake
from field_intake_bridge import (
    BridgePaths,
    PaperclipBridgeError,
    build_approval_gates,
    build_command_record,
    build_delegation_plan,
    build_matter_brief,
    build_matter_workspace_manifest,
    build_paperclip_issue_requests,
    build_partner_briefing,
    load_json,
    request_json,
)
from folder_planner import plan_client_matter_folders
from live_file import build_live_file
from legal_knowledge import infer_required_documents


ARTIFACT_KEYS = [
    "source_index",
    "transcript_index",
    "document_inventory",
    "client_profile",
    "matter_brief",
    "memory_update",
    "control_master_update",
    "missing_info",
    "corrections_ledger",
    "engagement_update",
    "delegation_plan",
    "paperclip_issue_requests",
    "dashboard_snapshot",
    "partner_briefing",
    "partner_action_packets",
]

VALID_MODES = {"drive_migration", "new_client_conversation"}
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_EXPORT_MIME = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}
TEXT_MIME_PREFIXES = ("text/",)
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CONTROL_MASTER_HEADERS = {
    "Clientes": ["timestamp", "cliente", "estado", "source_folder", "packet_id"],
    "Matters": ["timestamp", "cliente", "matter", "estado", "documentos_requeridos", "packet_id"],
    "Fuentes": ["timestamp", "source_id", "nombre", "categoria", "path", "url", "has_text", "packet_id"],
    "Transcripciones": ["timestamp", "source_id", "nombre", "path", "packet_id"],
    "Documentos": ["timestamp", "document_type", "title", "status", "packet_id"],
    "Faltantes": ["timestamp", "field", "taxonomy", "reason", "packet_id"],
    "Correcciones": ["timestamp", "target", "instruction", "source_id", "status", "packet_id"],
    "Tareas": ["timestamp", "role", "title", "priority", "packet_id"],
    "Aprobaciones": ["timestamp", "type", "status", "owner", "reason", "packet_id"],
    "Cobranza": ["timestamp", "status", "amounts", "flags", "packet_id"],
}


def build_intake_orchestrator_packet(
    *,
    mode: str,
    partner_context: str = "",
    drive_folder_url: str | None = None,
    conversation_text: str | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the standard Hermes office packet for a client intake command.

    This first layer is intentionally local/dry-run. It standardizes the command
    shape before any live Drive, Sheets, Docs or Paperclip mutation is allowed.
    """

    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported intake orchestrator mode: {mode}")
    if mode == "drive_migration" and not drive_folder_url:
        raise ValueError("drive_migration requires drive_folder_url")
    if mode == "new_client_conversation" and not conversation_text:
        raise ValueError("new_client_conversation requires conversation_text")

    normalized_sources = normalize_sources(sources or [], conversation_text=conversation_text)
    source_index = build_source_index(normalized_sources)
    intake_sources = [
        {"id": item["id"], "title": item["name"], "text": item.get("text", "")}
        for item in normalized_sources
        if classify_source(item) in {"transcript", "review"} and item.get("text")
    ]
    transcript_intake = build_transcript_intake(intake_sources) if intake_sources else empty_transcript_intake()
    required_documents = merge_required_documents(
        transcript_intake["required_documents"],
        infer_required_documents_from_all_sources(normalized_sources, partner_context),
    )
    corrections = expand_corrections(transcript_intake["corrections"])
    missing_info = transcript_intake["missing_info"]
    data_ledger = transcript_intake["data_ledger"]
    engagement_update = build_engagement_update(partner_context, normalized_sources)

    transcript_index = {
        "kind": "transcript_index",
        "sources": [item for item in source_index["sources"] if item["category"] in {"transcript", "review"}],
    }
    document_inventory = {
        "kind": "document_inventory",
        "sources": [item for item in source_index["sources"] if item["category"] in {"existing_doc", "draft", "deliverable"}],
    }

    combined_text = "\n".join(
        [
            partner_context,
            *[item.get("name", "") for item in normalized_sources],
            *[item.get("path", "") or "" for item in normalized_sources],
            *[item.get("text", "") for item in normalized_sources],
        ]
    )
    client_name = data_ledger.get("cliente.nombre", {}).get("value") or extract_labeled_value(combined_text, "Cliente") or infer_client_name(combined_text)
    matter_description = data_ledger.get("matter.descripcion", {}).get("value") or extract_labeled_value(combined_text, "Proyecto") or infer_matter_description_from_text(combined_text)

    client_profile = {
        "kind": "client_profile",
        "name": client_name or "Cliente por confirmar",
        "status": "candidate",
        "source": "drive_folder" if mode == "drive_migration" else "conversation",
        "data_ledger": {key: value for key, value in data_ledger.items() if key.startswith("cliente.")},
    }
    matter_brief_base = {
        "kind": "matter_brief",
        "description": matter_description or "Asunto por clasificar",
        "status": "intake",
        "controller": "hermes",
        "staff_system": "paperclip",
        "required_documents": required_documents,
        "reviewers": transcript_intake["reviewers"],
        "evidence_map": transcript_intake["evidence_map"],
    }
    office_context = build_office_context(
        mode=mode,
        partner_context=partner_context,
        drive_folder_url=drive_folder_url,
        client_name=client_profile["name"],
        matter_description=matter_brief_base["description"],
        required_documents=required_documents,
        missing_info=missing_info,
    )
    client_contract = office_context["client"]
    matter_contract = office_context["matter"]
    source_folder = drive_folder_descriptor(drive_folder_url) if drive_folder_url else None
    packet_fingerprint = build_packet_fingerprint(
        mode=mode,
        client_id=client_contract["id"],
        matter_id=matter_contract["id"],
        drive_folder_id=(source_folder or {}).get("id"),
        sources=normalized_sources,
        required_documents=required_documents,
    )
    partner_action_packets = build_partner_action_packets(
        client=client_contract,
        matter=matter_contract,
        missing_info=missing_info,
        required_documents=required_documents,
    )

    artifacts = {
        "source_index": source_index,
        "transcript_index": transcript_index,
        "document_inventory": document_inventory,
        "client_profile": client_profile,
        "matter_brief": {**matter_brief_base, **office_context["matter_brief"]},
        "memory_update": build_memory_update(client_name, matter_description, partner_context, transcript_intake),
        "control_master_update": build_control_master_update(client_name, matter_description, required_documents, engagement_update),
        "missing_info": {"kind": "missing_info", "items": missing_info},
        "corrections_ledger": {"kind": "corrections_ledger", "items": corrections},
        "engagement_update": engagement_update,
        "command_record": office_context["command_record"],
        "workspace_manifest": office_context["workspace_manifest"],
        "approval_gates": office_context["approval_gates"],
        "delegation_plan": office_context["delegation_plan"],
        "paperclip_issue_requests": office_context["paperclip_issue_requests"],
        "dashboard_snapshot": office_context["dashboard_snapshot"],
        "partner_briefing": office_context["partner_briefing"],
        "partner_action_packets": partner_action_packets,
    }

    return {
        "kind": "hermes_intake_orchestrator_packet",
        "mode": mode,
        "created_at": now(),
        "idempotency_key": packet_fingerprint,
        "controller": "hermes",
        "staff_system": "paperclip",
        "chain_of_command": ["pablo", "hermes", "paperclip_staff", "workspace", "dashboard"],
        "partner_context": partner_context,
        "client": client_contract,
        "matter": matter_contract,
        "missing_info": missing_info,
        "required_documents": required_documents,
        "senior_status": {
            "status": "pending_review",
            "decision": "not_reviewed",
            "reason": "Senior Review has not reviewed the current package yet.",
        },
        "paperclip": {
            "mode": "delegation_plan_ready",
            "issue_request_count": len(office_context["paperclip_issue_requests"]),
            "roles": [item["role"] for item in office_context["paperclip_issue_requests"]],
        },
        "drive_folder": source_folder,
        "workspace": {
            "read": {"mode": "provided_sources"},
            "source_folder": source_folder,
            "control_master": {"mode": "not_written"},
            "packet_file": {"mode": "not_written"},
            "document_writeback": build_document_writeback_decision(normalized_sources),
            "idempotency": {"key": packet_fingerprint},
            "write_gate": {
                "approved": False,
                "mode": "dry_run",
                "requirement": "explicit user approval and configured Hermes Workspace credentials",
            }
        },
        "artifacts": artifacts,
    }


def build_live_drive_intake_packet(
    *,
    drive_folder_url: str,
    partner_context: str = "",
    drive_client: "GwsDriveClient | None" = None,
) -> dict[str, Any]:
    """Read a live Drive folder through Hermes credentials and build an intake packet."""

    client = drive_client or GwsDriveClient()
    sources = client.read_folder_sources(drive_folder_url)
    packet = build_intake_orchestrator_packet(
        mode="drive_migration",
        drive_folder_url=drive_folder_url,
        partner_context=partner_context,
        sources=sources,
    )
    packet["workspace"]["read"] = {
        "mode": "live_gws",
        "source_count": len(sources),
        "folder_id": extract_drive_folder_id(drive_folder_url),
    }
    packet["workspace"]["source_folder"] = drive_folder_descriptor(drive_folder_url)
    packet["workspace"]["write_gate"] = {
        "approved": False,
        "mode": "approval_required",
        "requirement": "Drive/Sheets writes require explicit approval; this live run only reads Drive and can create Paperclip issues if requested.",
    }
    return packet


def persist_intake_orchestrator_packet(
    packet: dict[str, Any],
    *,
    output_root: str | Path | None = None,
) -> Path:
    """Persist a dry-run intake packet for dashboard and audit consumption."""

    target_root = Path(output_root) if output_root is not None else ROOT / "workspace/generated/intake-orchestrator"
    target_root.mkdir(parents=True, exist_ok=True)
    created_at = str(packet.get("created_at") or now()).replace(":", "").replace("-", "")
    mode = str(packet.get("mode") or "intake")
    filename = f"{created_at}-{mode}.json"
    path = target_root / filename
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def persist_partner_action_packets(
    packet: dict[str, Any],
    *,
    output_root: str | Path | None = None,
) -> dict[str, str]:
    artifacts = packet.get("artifacts", {})
    partner_actions = artifacts.get("partner_action_packets", {}) if isinstance(artifacts, dict) else {}
    matter = packet.get("matter", {}) if isinstance(packet.get("matter"), dict) else {}
    aliases = matter.get("legacy_aliases", []) if isinstance(matter.get("legacy_aliases"), list) else []
    matter_id = str(aliases[0] if aliases else matter.get("id") or "MAT-DEMO-HEALTH-SAAS")
    target_root = Path(output_root) if output_root is not None else ROOT / "workspace/matters" / matter_id / "partner-actions"
    target_root.mkdir(parents=True, exist_ok=True)
    missing_info_path = target_root / "MISSING_INFO_REQUEST.md"
    approval_path = target_root / "PARTNER_APPROVAL_PACKET.md"
    missing_info_path.write_text(str(partner_actions.get("missing_info_request_markdown") or ""), encoding="utf-8")
    approval_path.write_text(str(partner_actions.get("partner_approval_packet_markdown") or ""), encoding="utf-8")
    return {
        "missing_info_request": str(missing_info_path),
        "partner_approval_packet": str(approval_path),
    }


def run_live_drive_intake(
    *,
    drive_folder_url: str,
    partner_context: str = "",
    drive_client: "GwsDriveClient | None" = None,
    apply_local: bool = False,
    apply_paperclip: bool = False,
    apply_workspace: bool = False,
    packet_output_root: str | Path | None = None,
    api_url: str | None = None,
    paperclip_apply: Any | None = None,
    workspace_writer: "GwsWorkspaceWriter | None" = None,
) -> dict[str, Any]:
    packet = build_live_drive_intake_packet(
        drive_folder_url=drive_folder_url,
        partner_context=partner_context,
        drive_client=drive_client,
    )
    persisted_path: Path | None = None
    partner_action_paths: dict[str, str] | None = None
    if apply_local:
        persisted_path = persist_intake_orchestrator_packet(packet, output_root=packet_output_root)
        partner_action_paths = persist_partner_action_packets(packet)
    created_issues = []
    workspace_writeback = None
    if apply_workspace:
        workspace_writeback = apply_workspace_writeback(packet, writer=workspace_writer)
    attach_runtime_context_to_paperclip_requests(
        packet,
        persisted_path=persisted_path,
        workspace_writeback=workspace_writeback,
    )
    if apply_paperclip:
        apply_fn = paperclip_apply or apply_intake_packet_to_paperclip
        created_issues = apply_fn(packet, api_url=api_url)
    return {
        "ok": True,
        "packet": packet,
        "persisted_packet": str(persisted_path) if persisted_path else None,
        "paperclip_created": created_issues,
        "workspace_writeback": workspace_writeback,
        "partner_action_paths": partner_action_paths,
    }


def apply_workspace_writeback(
    packet: dict[str, Any],
    *,
    writer: "GwsWorkspaceWriter | None" = None,
) -> dict[str, Any]:
    active_writer = writer or GwsWorkspaceWriter()
    return active_writer.write_intake_packet(packet)


def attach_runtime_context_to_paperclip_requests(
    packet: dict[str, Any],
    *,
    persisted_path: Path | str | None = None,
    workspace_writeback: dict[str, Any] | None = None,
) -> None:
    """Embed the minimum live context in issue bodies before Paperclip runs.

    Paperclip adapters do not guarantee that arbitrary structured fields such as
    `context_package` are visible to the model. The issue description is the
    contract workers reliably see, so production runs must carry the source,
    packet and canonical-root guard directly in the body.
    """

    artifacts = packet.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return
    issue_requests = artifacts.get("paperclip_issue_requests", [])
    if not isinstance(issue_requests, list):
        return

    context = build_runtime_issue_context(
        packet,
        persisted_path=persisted_path,
        workspace_writeback=workspace_writeback,
    )
    for issue in issue_requests:
        if not isinstance(issue, dict):
            continue
        description = str(issue.get("description") or "")
        if "HERMES WE LAW RUNTIME CONTEXT" in description:
            continue
        issue["description"] = f"{description}\n\n{context}".strip()


def build_runtime_issue_context(
    packet: dict[str, Any],
    *,
    persisted_path: Path | str | None = None,
    workspace_writeback: dict[str, Any] | None = None,
) -> str:
    artifacts = packet.get("artifacts", {})
    source_index = artifacts.get("source_index", {}) if isinstance(artifacts, dict) else {}
    sources = source_index.get("sources", []) if isinstance(source_index, dict) else []
    source_lines = []
    for source in sources[:30]:
        if not isinstance(source, dict):
            continue
        source_lines.append(
            "- {category}: {name} | path={path} | has_text={has_text}".format(
                category=source.get("category", "unknown"),
                name=source.get("name", "sin nombre"),
                path=source.get("path") or source.get("id") or "",
                has_text=source.get("has_text", False),
            )
        )
    if len(sources) > 30:
        source_lines.append(f"- ... {len(sources) - 30} fuentes adicionales en el paquete.")

    workspace_lines: list[str] = []
    if workspace_writeback:
        workspace = packet.setdefault("workspace", {})
        workspace["control_master"] = {
            "spreadsheet_id": workspace_writeback.get("spreadsheet_id"),
            "url": workspace_writeback.get("spreadsheet_url"),
            "idempotent": workspace_writeback.get("idempotent", False),
        }
        workspace["packet_file"] = workspace_writeback.get("packet_file") or {}
        workspace_lines.extend(
            [
                f"- Control Maestro Sheet: {workspace_writeback.get('spreadsheet_url') or workspace_writeback.get('spreadsheet_id')}",
                f"- Packet JSON Drive: {(workspace_writeback.get('packet_file') or {}).get('webViewLink') or (workspace_writeback.get('packet_file') or {}).get('id')}",
            ]
        )

    local_packet = str(persisted_path) if persisted_path else "pendiente/no persistido"
    drive_folder = packet.get("drive_folder", {}) if isinstance(packet.get("drive_folder"), dict) else {}
    drive_folder_url = drive_folder.get("url") or "n/a"

    return "\n".join(
        [
            "HERMES WE LAW RUNTIME CONTEXT",
            f"- Canonical production root: {ROOT}",
            "- Forbidden root: ${HERMES_WELAW_FORBIDDEN_ROOT:-/path/to/noncanonical-backup}",
            "- If your process starts inside a Paperclip workspace, still write legal work products under the canonical production root paths below.",
            "- Never write new work products to the forbidden root. If you see that root in prior artifacts, report BLOCKER_RUTA_CANONICA.",
            f"- Local intake packet: {local_packet}",
            f"- Source Drive folder: {drive_folder_url}",
            "- Canonical matter output root: "
            f"{ROOT / 'workspace/matters' / str((artifacts.get('matter_brief') or {}).get('matter_id', 'MAT-DEMO-HEALTH-SAAS'))}",
            "Workspace writeback:",
            *(workspace_lines or ["- No Workspace writeback attached to this issue."]),
            "Source index:",
            *(source_lines or ["- No sources available in issue context."]),
        ]
    )


def apply_intake_packet_to_paperclip(
    packet: dict[str, Any],
    *,
    api_url: str | None = None,
    request_json_fn: Any = request_json,
    wait_sec: int = 900,
    poll_sec: int = 10,
) -> list[dict[str, Any]]:
    manifest = load_json(BridgePaths().manifest, {})
    api = (api_url or manifest.get("apiUrl") or "http://127.0.0.1:3100/api").rstrip("/")
    created = []
    parent_id: str | None = None
    issue_requests = packet.get("artifacts", {}).get("paperclip_issue_requests", [])
    parent_requests = [issue for issue in issue_requests if issue.get("role") == "master"]
    foundation_requests = [
        issue
        for issue in issue_requests
        if issue.get("role") not in {"master", "documents", "editorial", "senior_review"}
    ]
    document_requests = [issue for issue in issue_requests if issue.get("role") == "documents"]
    editorial_requests = [issue for issue in issue_requests if issue.get("role") == "editorial"]
    review_requests = [issue for issue in issue_requests if issue.get("role") == "senior_review"]

    for issue in parent_requests:
        response = create_paperclip_issue(api, manifest, issue, parent_id, request_json_fn)
        parent_id = response.get("id") or parent_id
        created.append({"role": issue["role"], "issue": response})

    foundation_created = []
    for issue in foundation_requests:
        response = create_paperclip_issue(api, manifest, issue, parent_id, request_json_fn)
        foundation_created.append({"role": issue["role"], "issue": response})
        created.append(foundation_created[-1])
    wait_for_created_issues(api, foundation_created, request_json_fn, wait_sec=wait_sec, poll_sec=poll_sec)

    for issue in document_requests:
        response = create_paperclip_issue(api, manifest, issue, parent_id, request_json_fn)
        item = {"role": issue["role"], "issue": response}
        created.append(item)
        wait_for_created_issues(api, [item], request_json_fn, wait_sec=wait_sec, poll_sec=poll_sec)

    editorial_created = []
    for issue in editorial_requests:
        response = create_paperclip_issue(api, manifest, issue, parent_id, request_json_fn)
        editorial_created.append({"role": issue["role"], "issue": response})
        created.append(editorial_created[-1])
    wait_for_created_issues(api, editorial_created, request_json_fn, wait_sec=wait_sec, poll_sec=poll_sec)

    review_created = []
    for issue in review_requests:
        response = create_paperclip_issue(api, manifest, issue, parent_id, request_json_fn)
        review_created.append({"role": issue["role"], "issue": response})
        created.append(review_created[-1])
    wait_for_created_issues(api, review_created, request_json_fn, wait_sec=wait_sec, poll_sec=poll_sec)
    return created


def create_paperclip_issue(
    api: str,
    manifest: dict[str, Any],
    issue: dict[str, Any],
    parent_id: str | None,
    request_json_fn: Any,
) -> dict[str, Any]:
    body = {
        "title": issue["title"],
        "description": issue["description"],
        "status": "todo",
        "priority": issue.get("priority", "medium"),
    }
    if issue.get("assigneeAgentId"):
        body["assigneeAgentId"] = issue["assigneeAgentId"]
    if parent_id:
        body["parentId"] = parent_id
    company_id = issue.get("company_id") or manifest.get("companyId")
    if not company_id:
        raise PaperclipBridgeError("Missing Paperclip company id for intake issue creation")
    return request_json_fn("POST", f"{api}/companies/{company_id}/issues", body)


def wait_for_created_issues(
    api: str,
    created: list[dict[str, Any]],
    request_json_fn: Any,
    *,
    wait_sec: int,
    poll_sec: int,
) -> None:
    if not created or wait_sec <= 0:
        return
    deadline = time.time() + wait_sec
    pending = {item["issue"]["id"]: item for item in created if item.get("issue", {}).get("id")}
    terminal = {"done", "cancelled", "blocked"}
    while pending and time.time() < deadline:
        for issue_id in list(pending):
            issue = request_json_fn("GET", f"{api}/issues/{issue_id}")
            status = issue.get("status")
            if status in terminal:
                if status != "done":
                    identifier = issue.get("identifier", issue_id)
                    raise PaperclipBridgeError(f"Paperclip issue {identifier} ended {status}; stopping phased intake")
                pending.pop(issue_id, None)
        if pending:
            time.sleep(max(poll_sec, 1))
    if pending:
        identifiers = [item["issue"].get("identifier", issue_id) for issue_id, item in pending.items()]
        raise PaperclipBridgeError(f"Timed out waiting for Paperclip issues: {', '.join(identifiers)}")


def check_paperclip_staff_ready(
    *,
    api_url: str | None = None,
    request_json_fn: Any = request_json,
) -> dict[str, Any]:
    manifest = load_json(BridgePaths().manifest, {})
    api = (api_url or manifest.get("apiUrl") or "http://127.0.0.1:3100/api").rstrip("/")
    company_id = manifest.get("companyId")
    expected_agents = manifest.get("agents", {})
    if not company_id:
        return {"ok": False, "reason": "missing_company_id"}
    agents = request_json_fn("GET", f"{api}/companies/{company_id}/agents")
    if not isinstance(agents, list):
        return {"ok": False, "reason": "agents_endpoint_not_list"}
    by_id = {agent.get("id"): agent for agent in agents if isinstance(agent, dict)}
    bad = []
    missing = []
    for role, agent_id in expected_agents.items():
        agent = by_id.get(agent_id)
        if not agent:
            missing.append({"role": role, "agent_id": agent_id})
            continue
        status = agent.get("status")
        if status == "error":
            bad.append({"role": role, "agent_id": agent_id, "name": agent.get("name"), "status": status})
    return {
        "ok": not bad and not missing,
        "reason": "paperclip_staff_ready" if not bad and not missing else "paperclip_staff_not_ready",
        "company_id": company_id,
        "bad_agents": bad,
        "missing_agents": missing,
    }


class GwsCommandRunner:
    def __init__(self, *, credentials_file: str | None = None):
        self.credentials_file = credentials_file or str(Path.home() / ".hermes/profiles/welaw/google_token.json")

    def json(self, command: list[str]) -> dict[str, Any]:
        result = self._run(command)
        return json.loads(result.stdout or "{}")

    def output(self, command: list[str], suffix: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            output_path = Path(handle.name)
        try:
            self._run([*command, "--output", str(output_path)])
            return extract_text_from_file(output_path)
        finally:
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.setdefault("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", self.credentials_file)
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )


class GwsWorkspaceWriter:
    root_folder_name = "Hermes We Law OS"
    spreadsheet_name = "Hermes We Law OS - Control Maestro"

    def __init__(
        self,
        *,
        runner: Any | None = None,
        config_path: str | Path | None = None,
    ):
        self.runner = runner or GwsCommandRunner()
        self.config_path = Path(config_path) if config_path is not None else ROOT / "runtime/config/welaw-control-master.json"

    def write_intake_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        config = self.load_or_bootstrap_config()
        packet_key = packet.get("idempotency_key") or stable_json_hash(packet.get("artifacts", {}))
        written_keys = set(config.get("written_packet_keys", []))
        spreadsheet_id = config["spreadsheet_id"]
        self.ensure_spreadsheet_tabs(spreadsheet_id)
        rows_by_table = rows_for_control_master(packet)
        tables_written = []
        if packet_key not in written_keys:
            for table, rows in rows_by_table.items():
                if not rows:
                    continue
                self.append_values(spreadsheet_id, table, rows)
                tables_written.append(table)
        packet_file = self.upload_packet_json(config["folder_id"], packet)
        if packet_key not in written_keys:
            config.setdefault("written_packet_keys", []).append(packet_key)
            self.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "folder_id": config["folder_id"],
            "folder_url": config.get("folder_url"),
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": config.get("spreadsheet_url"),
            "tables_written": tables_written,
            "packet_file": packet_file,
            "idempotency_key": packet_key,
            "idempotent": packet_key in written_keys,
        }

    def load_or_bootstrap_config(self) -> dict[str, Any]:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        folder = self.find_or_create_folder(self.root_folder_name)
        spreadsheet = self.find_or_create_spreadsheet(self.spreadsheet_name, folder["id"])
        config = {
            "kind": "welaw_control_master",
            "folder_id": folder["id"],
            "folder_url": folder.get("webViewLink"),
            "spreadsheet_id": spreadsheet["id"],
            "spreadsheet_url": spreadsheet.get("webViewLink") or spreadsheet.get("spreadsheetUrl"),
            "created_at": now(),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return config

    def find_or_create_folder(self, name: str) -> dict[str, Any]:
        existing = self.find_drive_file(name, GOOGLE_FOLDER_MIME)
        if existing:
            return existing
        return self.runner.json(
            [
                "gws",
                "drive",
                "files",
                "create",
                "--json",
                json.dumps({"name": name, "mimeType": GOOGLE_FOLDER_MIME}),
                "--format",
                "json",
            ]
        )

    def find_or_create_spreadsheet(self, name: str, folder_id: str) -> dict[str, Any]:
        existing = self.find_drive_file(name, "application/vnd.google-apps.spreadsheet")
        if existing:
            return existing
        return self.runner.json(
            [
                "gws",
                "drive",
                "files",
                "create",
                "--json",
                json.dumps(
                    {
                        "name": name,
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                        "parents": [folder_id],
                    }
                ),
                "--format",
                "json",
            ]
        )

    def find_drive_file(self, name: str, mime_type: str) -> dict[str, Any] | None:
        query = f"name = '{escape_drive_query(name)}' and mimeType = '{mime_type}' and trashed=false"
        result = self.runner.json(
            [
                "gws",
                "drive",
                "files",
                "list",
                "--params",
                json.dumps({"q": query, "pageSize": 10, "fields": "files(id,name,mimeType,webViewLink,parents)"}),
                "--format",
                "json",
            ]
        )
        files = result.get("files", [])
        return files[0] if files else None

    def ensure_spreadsheet_tabs(self, spreadsheet_id: str) -> None:
        metadata = self.runner.json(
            [
                "gws",
                "sheets",
                "spreadsheets",
                "get",
                "--params",
                json.dumps({"spreadsheetId": spreadsheet_id, "fields": "sheets.properties"}),
                "--format",
                "json",
            ]
        )
        sheets = metadata.get("sheets", [])
        existing = {
            sheet.get("properties", {}).get("title"): sheet.get("properties", {}).get("sheetId")
            for sheet in sheets
        }
        requests = []
        if "Sheet1" in existing and "Clientes" not in existing:
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": existing["Sheet1"], "title": "Clientes"},
                        "fields": "title",
                    }
                }
            )
            existing["Clientes"] = existing.pop("Sheet1")
        for table in CONTROL_MASTER_HEADERS:
            if table in existing:
                continue
            requests.append({"addSheet": {"properties": {"title": table}}})
        if requests:
            self.runner.json(
                [
                    "gws",
                    "sheets",
                    "spreadsheets",
                    "batchUpdate",
                    "--params",
                    json.dumps({"spreadsheetId": spreadsheet_id}),
                    "--json",
                    json.dumps({"requests": requests}),
                    "--format",
                    "json",
                ]
            )
        for table, headers in CONTROL_MASTER_HEADERS.items():
            self.update_values(spreadsheet_id, f"{quote_sheet_name(table)}!A1:{column_letter(len(headers))}1", [headers])

    def update_values(self, spreadsheet_id: str, range_name: str, rows: list[list[Any]]) -> dict[str, Any]:
        return self.runner.json(
            [
                "gws",
                "sheets",
                "spreadsheets",
                "values",
                "update",
                "--params",
                json.dumps({"spreadsheetId": spreadsheet_id, "range": range_name, "valueInputOption": "USER_ENTERED"}),
                "--json",
                json.dumps({"values": rows}),
                "--format",
                "json",
            ]
        )

    def append_values(self, spreadsheet_id: str, table: str, rows: list[list[Any]]) -> dict[str, Any]:
        return self.runner.json(
            [
                "gws",
                "sheets",
                "spreadsheets",
                "values",
                "append",
                "--params",
                json.dumps(
                    {
                        "spreadsheetId": spreadsheet_id,
                        "range": f"{quote_sheet_name(table)}!A1",
                        "valueInputOption": "USER_ENTERED",
                        "insertDataOption": "INSERT_ROWS",
                    }
                ),
                "--json",
                json.dumps({"values": rows}),
                "--format",
                "json",
            ]
        )

    def upload_packet_json(self, folder_id: str, packet: dict[str, Any]) -> dict[str, Any]:
        packet_key = packet.get("idempotency_key") or stable_json_hash(packet.get("artifacts", {}))
        name = f"{packet_key}-intake-packet.json"
        existing = self.find_drive_file(name, "application/json")
        if existing:
            return {**existing, "idempotent": True}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(packet, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)
        try:
            return self.runner.json(
                [
                    "gws",
                    "drive",
                    "files",
                    "create",
                    "--json",
                    json.dumps({"name": name, "parents": [folder_id], "mimeType": "application/json"}),
                    "--upload",
                    str(temp_path),
                    "--format",
                    "json",
                ]
            )
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


class GwsDriveClient:
    def __init__(self, *, runner: Any | None = None, max_depth: int = 8):
        self.runner = runner or GwsCommandRunner()
        self.max_depth = max_depth

    def read_folder_sources(self, drive_folder_url: str) -> list[dict[str, Any]]:
        folder_id = extract_drive_folder_id(drive_folder_url)
        return self._read_folder(folder_id, path_prefix="", depth=0)

    def _read_folder(self, folder_id: str, *, path_prefix: str, depth: int) -> list[dict[str, Any]]:
        if depth > self.max_depth:
            return []
        sources: list[dict[str, Any]] = []
        folders: list[dict[str, Any]] = []
        for item in self._list_children(folder_id):
            name = item.get("name", item.get("id", "sin-nombre"))
            mime_type = item.get("mimeType", "")
            item_path = f"{path_prefix}/{name}".strip("/")
            if mime_type == GOOGLE_FOLDER_MIME:
                folders.append({"id": item["id"], "path": item_path})
                continue
            sources.append(self._file_to_source(item, item_path))
        for folder in folders:
            sources.extend(self._read_folder(folder["id"], path_prefix=folder["path"], depth=depth + 1))
        return sources

    def _list_children(self, folder_id: str) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed=false",
            "pageSize": 100,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "fields": "files(id,name,mimeType,webViewLink,modifiedTime,size),nextPageToken",
        }
        files: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            else:
                params.pop("pageToken", None)
            result = self.runner.json(["gws", "drive", "files", "list", "--params", json.dumps(params), "--format", "json"])
            files.extend(list(result.get("files", [])))
            page_token = result.get("nextPageToken")
            if not page_token:
                return files

    def _file_to_source(self, item: dict[str, Any], item_path: str) -> dict[str, Any]:
        mime_type = item.get("mimeType", "")
        text = ""
        read_error = None
        try:
            text = self._read_file_text(item.get("id", ""), mime_type)
        except Exception as exc:
            read_error = str(exc)
        return {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "mime_type": mime_type,
            "url": item.get("webViewLink"),
            "path": item_path,
            "text": text,
            "read_error": read_error,
            "modified_time": item.get("modifiedTime"),
        }

    def _read_file_text(self, file_id: str, mime_type: str) -> str:
        if not file_id:
            return ""
        if mime_type in GOOGLE_EXPORT_MIME:
            export_mime, suffix = GOOGLE_EXPORT_MIME[mime_type]
            return self.runner.output(
                [
                    "gws",
                    "drive",
                    "files",
                    "export",
                    "--params",
                    json.dumps({"fileId": file_id, "mimeType": export_mime}),
                ],
                suffix,
            )
        suffix = suffix_for_mime(mime_type)
        if mime_type.startswith(TEXT_MIME_PREFIXES) or mime_type in {PDF_MIME, DOCX_MIME}:
            return self.runner.output(
                [
                    "gws",
                    "drive",
                    "files",
                    "get",
                    "--params",
                    json.dumps({"fileId": file_id, "alt": "media", "supportsAllDrives": True}),
                ],
                suffix,
            )
        return ""


def normalize_sources(
    sources: list[dict[str, Any]],
    *,
    conversation_text: str | None = None,
) -> list[dict[str, Any]]:
    normalized = [
        {
            "id": str(item.get("id") or f"SRC-{index:03d}"),
            "name": str(item.get("name") or item.get("title") or f"Fuente {index:03d}"),
            "mime_type": str(item.get("mime_type") or item.get("mimeType") or "text/plain"),
            "text": str(item.get("text") or ""),
            "url": item.get("url"),
            "path": item.get("path"),
            "read_error": item.get("read_error"),
        }
        for index, item in enumerate(sources, start=1)
    ]
    if conversation_text:
        normalized.append(
            {
                "id": "CONV-001",
                "name": "Conversacion inicial",
                "mime_type": "text/plain",
                "text": conversation_text,
                "url": None,
                "path": "Conversacion inicial",
            }
        )
    return normalized


def build_source_index(sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "source_index",
        "source_count": len(sources),
        "sources": [
            {
                "id": item["id"],
                "name": item["name"],
                "mime_type": item["mime_type"],
                "category": classify_source(item),
                "has_text": bool(item.get("text")),
                "url": item.get("url"),
                "path": item.get("path"),
                "read_error": item.get("read_error"),
            }
            for item in sources
        ],
    }


def classify_source(source: dict[str, Any]) -> str:
    name = normalize(source.get("name", ""))
    path = normalize(source.get("path", ""))
    if any(token in path for token in ["transcripcion", "transcripciones", "demo notes", "reunion", "seguimiento"]):
        return "transcript"
    if any(token in path for token in ["revision", "revisiones", "correccion", "correcciones"]):
        return "review"
    if any(token in name for token in ["transcripcion", "transcripción", "minuta", "llamada"]):
        return "transcript"
    if "demo notes" in name or "demo health legal project" in name or "follow up meeting" in name:
        return "transcript"
    if any(token in name for token in ["revision", "revisión", "correccion", "corrección", "comentarios"]):
        return "review"
    if any(token in name for token in ["final", "entregable", "cliente"]):
        return "deliverable"
    if any(token in name for token in ["borrador", "draft", "v1", "v2", "trabajo"]):
        return "draft"
    if any(token in name for token in ["contrato", "aviso", "nda", "terminos", "términos", "arco", "convenio"]):
        return "existing_doc"
    if any(token in name for token in ["honorario", "pago", "cotizacion", "cotización", "engagement"]):
        return "billing_engagement"
    if "http" in str(source.get("text", "")).lower() or str(source.get("url") or "").startswith("http"):
        return "link"
    return "unknown"


def infer_required_documents_from_all_sources(sources: list[dict[str, Any]], partner_context: str) -> list[str]:
    combined = "\n".join(
        [
            partner_context,
            *[item.get("name", "") for item in sources],
            *[item.get("path", "") or "" for item in sources],
            *[item.get("text", "") for item in sources],
        ]
    )
    inferred = infer_required_documents(combined)
    normalized = normalize(combined)
    supplemental = []
    if ("medico" in normalized or "medicos" in normalized or "paciente" in normalized or "pacientes" in normalized) and "privacidad" in normalized:
        supplemental.append("aviso_privacidad_medicos_pacientes")
    return merge_required_documents(inferred, supplemental)


def merge_required_documents(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item not in merged:
                merged.append(item)
    return merged


def infer_client_name(text: str) -> str | None:
    normalized = normalize(text)
    if "demohealth" in normalized or "demo health" in normalized:
        return "Demo Health Platform / Demo Client Representative y Demo Co-Founder"
    if "demo health project" in normalized:
        return "Demo Health Platform Legal Project"
    return None


def infer_matter_description_from_text(text: str) -> str | None:
    normalized = normalize(text)
    if "demohealth" in normalized or "saas" in normalized or "software como servicio" in normalized:
        return "Paquete legal para plataforma SaaS Demo Health Platform"
    if "cotitularidad" in normalized and "desarrollo" in normalized:
        return "Paquete legal de software, desarrollo, privacidad y cotitularidad"
    return None


def empty_transcript_intake() -> dict[str, Any]:
    return {
        "kind": "transcript_intake",
        "source_count": 0,
        "client": {"name": "Cliente por confirmar"},
        "matter": {"description": "Asunto por clasificar"},
        "required_documents": [],
        "reviewers": [],
        "data_ledger": {},
        "evidence_map": {},
        "corrections": [],
        "missing_info": [],
    }


def build_engagement_update(partner_context: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    combined = "\n".join([partner_context, *[str(item.get("text") or "") for item in sources]])
    normalized = normalize(combined)
    amounts = dedupe(re.findall(r"\b\d{2,}(?:,\d{3})*(?:\.\d{2})?\b", combined))
    extra_signals = []
    if any(token in normalized for token in ["extra", "adicional", "posterior", "nueva contratacion", "nueva contratación"]):
        extra_signals.append("additional_work_detected")
    if any(token in normalized for token in ["paga", "pagara", "pagará", "honorario", "honorarios", "anticipo"]):
        extra_signals.append("billing_terms_detected")
    return {
        "kind": "engagement_update",
        "status": "pending_review" if amounts or extra_signals else "not_detected",
        "signals": {
            "amounts": amounts,
            "flags": extra_signals,
        },
    }


def expand_corrections(corrections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for correction in corrections:
        expanded.append(correction)
        instruction = normalize(correction.get("instruction", ""))
        extra_targets = []
        if ("desarrollo" in instruction or "software" in instruction or "repositorio" in instruction) and correction.get("target") != "contrato_desarrollo_software":
            extra_targets.append("contrato_desarrollo_software")
        if ("medico" in instruction or "paciente" in instruction) and correction.get("target") != "aviso_privacidad_medicos_pacientes":
            extra_targets.append("aviso_privacidad_medicos_pacientes")
        for target in extra_targets:
            item = dict(correction)
            item["target"] = target
            item["status"] = "pending_application"
            expanded.append(item)
    return expanded


def build_memory_update(
    client_name: str | None,
    matter_description: str | None,
    partner_context: str,
    transcript_intake: dict[str, Any],
) -> dict[str, Any]:
    facts = []
    if client_name:
        facts.append(f"Cliente identificado: {client_name}")
    if matter_description:
        facts.append(f"Asunto identificado: {matter_description}")
    if partner_context:
        facts.append(f"Contexto del socio: {partner_context}")
    for field, fact in transcript_intake.get("data_ledger", {}).items():
        facts.append(f"{field}: {fact.get('value')}")
    return {
        "kind": "memory_update",
        "proposed": True,
        "facts": facts,
    }


def build_control_master_update(
    client_name: str | None,
    matter_description: str | None,
    required_documents: list[str],
    engagement_update: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "control_master_update",
        "dry_run": True,
        "rows": [
            {"table": "Clientes", "values": {"nombre": client_name or "Cliente por confirmar", "estado": "candidate"}},
            {
                "table": "Matters",
                "values": {
                    "descripcion": matter_description or "Asunto por clasificar",
                    "estado": "intake",
                    "documentos_requeridos": required_documents,
                },
            },
            {"table": "Cobranza", "values": engagement_update["signals"]},
        ],
    }


def build_office_context(
    *,
    mode: str,
    partner_context: str,
    drive_folder_url: str | None,
    client_name: str,
    matter_description: str,
    required_documents: list[str],
    missing_info: list[dict[str, Any]],
) -> dict[str, Any]:
    client_id = build_client_id(client_name)
    matter_id = build_matter_id(client_name, matter_description)
    client = {
        "id": client_id,
        "nombre": client_name,
        "estado": "candidate",
        "rfc": "",
        "legacy_aliases": ["CLI-DEMO-HEALTH"] if client_id != "CLI-DEMO-HEALTH" else [],
    }
    matter = {
        "id": matter_id,
        "client_id": client["id"],
        "cliente": client["nombre"],
        "tipo": "contractual",
        "estado": "intake",
        "descripcion": matter_description,
        "fase": "migracion_drive" if mode == "drive_migration" else "intake_conversacional",
        "engagement": "pendiente",
        "legacy_aliases": ["MAT-DEMO-HEALTH-SAAS"] if matter_id != "MAT-DEMO-HEALTH-SAAS" else [],
    }
    folder_plan = plan_client_matter_folders(client, matter)
    client["drive_path"] = folder_plan["client_root"]
    matter["drive_path"] = folder_plan["matter_root"]
    documents = planned_document_records(matter, required_documents)
    tasks = planned_task_records(matter, required_documents, missing_info)
    live_file = build_live_file(client, matter, documents=documents, tasks=tasks, workspace=matter["drive_path"])
    parsed = {
        "matter_type": matter["tipo"],
        "requested_documents": required_documents,
        "risks": [item.get("field", item.get("reason", "faltante")) for item in missing_info],
        "confidence": 0.78,
    }
    legal_trigger = {"intent": "drive_folder_intake" if mode == "drive_migration" else "conversational_intake"}
    source_hint = f"Drive folder: {drive_folder_url}" if drive_folder_url else "Conversacion directa con Hermes"
    message = "\n".join([source_hint, partner_context]).strip()
    command_record = build_command_record(message, mode, client, matter, parsed, legal_trigger)
    matter_brief = build_matter_brief(client, matter, parsed, live_file, "", {"id": "INTAKE-DRYRUN"})
    workspace_manifest = build_matter_workspace_manifest(client, matter, folder_plan)
    approval_gates = build_approval_gates(parsed, matter)
    delegation_plan = build_delegation_plan(parsed, matter, documents, tasks, approval_gates)
    partner_briefing = build_partner_briefing(client, matter, delegation_plan, approval_gates)
    manifest = load_json(BridgePaths().manifest, {})
    paperclip_issue_requests = build_paperclip_issue_requests(
        manifest,
        message,
        client,
        matter,
        live_file,
        documents,
        tasks,
        command_record,
        matter_brief,
        delegation_plan,
        workspace_manifest,
        approval_gates,
    )
    dashboard_snapshot = {
        "kind": "dashboard_snapshot",
        "status": "intake_ready",
        "client_name": client["nombre"],
        "client_id": client["id"],
        "matter_description": matter["descripcion"],
        "matter_id": matter["id"],
        "legacy_matter_aliases": matter["legacy_aliases"],
        "mode": mode,
        "required_documents": required_documents,
        "missing_count": len(missing_info),
        "paperclip_roles": [item["role"] for item in paperclip_issue_requests],
    }
    return {
        "client": client,
        "matter": matter,
        "documents": documents,
        "tasks": tasks,
        "live_file": live_file,
        "command_record": command_record,
        "matter_brief": matter_brief,
        "workspace_manifest": workspace_manifest,
        "approval_gates": approval_gates,
        "delegation_plan": delegation_plan,
        "paperclip_issue_requests": paperclip_issue_requests,
        "partner_briefing": partner_briefing,
        "dashboard_snapshot": dashboard_snapshot,
    }


DOCUMENT_TITLES = {
    "terminos_condiciones": "Terminos y Condiciones",
    "aviso_privacidad_integral": "Aviso de Privacidad Integral",
    "aviso_privacidad_medicos_pacientes": "Aviso de Privacidad Medicos Pacientes",
    "formato_arco": "Formato ARCO",
    "nda": "NDA",
    "contrato_desarrollo_software": "Contrato de Desarrollo de Software",
    "convenio_cotitularidad": "Convenio de Cotitularidad",
    "contrato_prestacion": "Contrato de Prestacion de Servicios",
    "demanda_inicial": "Demanda Inicial",
    "memo_estrategia": "Memo de Estrategia",
    "aviso_privacidad": "Aviso de Privacidad",
}


def planned_document_records(matter: dict[str, Any], required_documents: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"DOC-DRY-{index:03d}",
            "matter_id": matter["id"],
            "type": document_type,
            "title": f"{DOCUMENT_TITLES.get(document_type, document_type)} - {matter['cliente']}",
            "status": "solicitado",
            "version": "v1",
            "drive_path": f"{matter['drive_path']}/04-Documentos en trabajo/{DOCUMENT_TITLES.get(document_type, document_type)}.md",
        }
        for index, document_type in enumerate(required_documents, start=1)
    ]


def planned_task_records(
    matter: dict[str, Any],
    required_documents: list[str],
    missing_info: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tasks = [
        {
            "id": "TRA-DRY-001",
            "matter_id": matter["id"],
            "title": "Consolidar expediente vivo desde fuentes de intake",
            "status": "todo",
            "owner": "Expediente / Records Manager",
            "priority": "high",
        },
        {
            "id": "TRA-DRY-002",
            "matter_id": matter["id"],
            "title": "Actualizar control maestro con cliente, matter, fuentes y faltantes",
            "status": "todo",
            "owner": "Data Clerk Google Sheets",
            "priority": "high",
        },
        {
            "id": "TRA-DRY-003",
            "matter_id": matter["id"],
            "title": "Determinar base juridica y riesgos del paquete",
            "status": "todo",
            "owner": "Analista Juridico",
            "priority": "high",
        },
    ]
    for index, document_type in enumerate(required_documents, start=4):
        tasks.append(
            {
                "id": f"TRA-DRY-{index:03d}",
                "matter_id": matter["id"],
                "title": f"Preparar {DOCUMENT_TITLES.get(document_type, document_type)}",
                "status": "todo",
                "owner": "Documentos Legales",
                "priority": "high",
            }
        )
    base = len(tasks) + 1
    if missing_info:
        tasks.append(
            {
                "id": f"TRA-DRY-{base:03d}",
                "matter_id": matter["id"],
                "title": "Cerrar faltantes de informacion para firma",
                "status": "todo",
                "owner": "Recepcionista Juridico",
                "priority": "high",
            }
        )
        base += 1
    tasks.extend(
        [
            {
                "id": f"TRA-DRY-{base:03d}",
                "matter_id": matter["id"],
                "title": "Preparar versiones editoriales y entregables al cliente",
                "status": "todo",
                "owner": "Produccion Editorial",
                "priority": "medium",
            },
            {
                "id": f"TRA-DRY-{base + 1:03d}",
                "matter_id": matter["id"],
                "title": "Revisar legalmente el paquete antes de entrega",
                "status": "todo",
                "owner": "Revisor Senior",
                "priority": "high",
            },
        ]
    )
    return tasks


def drive_folder_descriptor(url: str) -> dict[str, str]:
    return {"url": url, "id": extract_drive_folder_id(url)}


def build_client_id(client_name: str) -> str:
    normalized = normalize(client_name)
    if "demohealth" in normalized or "demo health" in normalized:
        return "CLI-DEMO-HEALTH"
    slug = slugify(client_name or "cliente")
    return f"CLI-{slug[:40]}" if slug else "CLI-CLIENTE-POR-CONFIRMAR"


def build_matter_id(client_name: str, matter_description: str) -> str:
    normalized = normalize(f"{client_name} {matter_description}")
    if "demohealth" in normalized and any(token in normalized for token in ["software", "saas", "privacidad", "cotitularidad"]):
        return "MAT-DEMO-HEALTH-SAAS"
    slug = slugify(matter_description or client_name or "asunto")
    return f"MAT-{slug[:48]}" if slug else "MAT-ASUNTO-POR-CLASIFICAR"


def slugify(value: str) -> str:
    normalized = normalize(value).upper()
    normalized = re.sub(r"[^A-Z0-9]+", "-", normalized).strip("-")
    return normalized or "SIN-ID"


def build_packet_fingerprint(
    *,
    mode: str,
    client_id: str,
    matter_id: str,
    drive_folder_id: str | None,
    sources: list[dict[str, Any]],
    required_documents: list[str],
) -> str:
    payload = {
        "mode": mode,
        "client_id": client_id,
        "matter_id": matter_id,
        "drive_folder_id": drive_folder_id,
        "sources": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "path": item.get("path"),
                "mime_type": item.get("mime_type"),
            }
            for item in sources
        ],
        "required_documents": required_documents,
    }
    return f"INTAKE-{stable_json_hash(payload)[:16].upper()}"


def stable_json_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def extract_drive_folder_id(url: str) -> str:
    match = re.search(r"/folders/([^/?#]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([^&#]+)", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


def suffix_for_mime(mime_type: str) -> str:
    if mime_type == PDF_MIME:
        return ".pdf"
    if mime_type == DOCX_MIME:
        return ".docx"
    if mime_type.startswith("text/"):
        return ".txt"
    return ".bin"


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".docx":
        return extract_docx_text(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def extract_pdf_text(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return ""


def extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as docx:
            xml = docx.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception:
        return ""
    text = re.sub(r"<[^>]+>", " ", xml)
    return " ".join(text.split())


def rows_for_control_master(packet: dict[str, Any]) -> dict[str, list[list[Any]]]:
    artifacts = packet.get("artifacts", {})
    timestamp = packet.get("created_at", now())
    packet_id = f"{timestamp}-{packet.get('mode', 'intake')}"
    snapshot = artifacts.get("dashboard_snapshot", {})
    client_profile = artifacts.get("client_profile", {})
    matter_brief = artifacts.get("matter_brief", {})
    drive_folder = packet.get("drive_folder") or {}
    source_items = artifacts.get("source_index", {}).get("sources", [])
    transcript_items = artifacts.get("transcript_index", {}).get("sources", [])
    document_items = artifacts.get("document_inventory", {}).get("sources", [])
    missing_items = artifacts.get("missing_info", {}).get("items", [])
    corrections = artifacts.get("corrections_ledger", {}).get("items", [])
    delegation = artifacts.get("delegation_plan", {}).get("assignments", [])
    approvals = artifacts.get("approval_gates", [])
    engagement = artifacts.get("engagement_update", {})
    required_documents = matter_brief.get("required_documents") or snapshot.get("required_documents", [])
    return {
        "Clientes": [
            [
                timestamp,
                client_profile.get("name") or snapshot.get("client_name") or "Cliente por confirmar",
                client_profile.get("status", "candidate"),
                drive_folder.get("url", ""),
                packet_id,
            ]
        ],
        "Matters": [
            [
                timestamp,
                client_profile.get("name") or snapshot.get("client_name") or "Cliente por confirmar",
                matter_brief.get("matter_description") or matter_brief.get("description") or snapshot.get("matter_description") or "Asunto por clasificar",
                matter_brief.get("status", "intake"),
                ", ".join(required_documents),
                packet_id,
            ]
        ],
        "Fuentes": [
            [
                timestamp,
                item.get("id", ""),
                item.get("name", ""),
                item.get("category", ""),
                item.get("path", ""),
                item.get("url", ""),
                str(bool(item.get("has_text"))),
                packet_id,
            ]
            for item in source_items
        ],
        "Transcripciones": [
            [timestamp, item.get("id", ""), item.get("name", ""), item.get("path", ""), packet_id]
            for item in transcript_items
        ],
        "Documentos": [
            [
                timestamp,
                item.get("category", ""),
                item.get("name", ""),
                "inventariado",
                packet_id,
            ]
            for item in document_items
        ],
        "Faltantes": [
            [
                timestamp,
                item.get("field", ""),
                item.get("taxonomy", ""),
                item.get("reason", ""),
                packet_id,
            ]
            for item in missing_items
        ],
        "Correcciones": [
            [
                timestamp,
                item.get("target", ""),
                item.get("instruction", ""),
                item.get("source_id", ""),
                item.get("status", ""),
                packet_id,
            ]
            for item in corrections
        ],
        "Tareas": [
            [
                timestamp,
                item.get("role", ""),
                item.get("title", ""),
                "high" if item.get("role") in {"master", "file", "sheets", "documents", "senior_review"} else "medium",
                packet_id,
            ]
            for item in delegation
        ],
        "Aprobaciones": [
            [
                timestamp,
                item.get("type", ""),
                item.get("status", ""),
                item.get("owner", ""),
                item.get("reason", ""),
                packet_id,
            ]
            for item in approvals
        ],
        "Cobranza": [
            [
                timestamp,
                engagement.get("status", ""),
                ", ".join(engagement.get("signals", {}).get("amounts", [])),
                ", ".join(engagement.get("signals", {}).get("flags", [])),
                packet_id,
            ]
        ],
    }


def build_partner_action_packets(
    *,
    client: dict[str, Any],
    matter: dict[str, Any],
    missing_info: list[dict[str, Any]],
    required_documents: list[str],
) -> dict[str, Any]:
    categories = categorize_missing_info(missing_info)
    missing_info_markdown = render_missing_info_request(client, matter, categories)
    approval_markdown = render_partner_approval_packet(client, matter, categories, required_documents)
    return {
        "kind": "partner_action_packets",
        "missing_info_categories": categories,
        "missing_info_request_markdown": missing_info_markdown,
        "partner_approval_packet_markdown": approval_markdown,
    }


def build_document_writeback_decision(sources: list[dict[str, Any]]) -> dict[str, Any]:
    source_summary = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "mime_type": item.get("mime_type") or item.get("mimeType"),
        }
        for item in sources
        if item.get("mime_type") or item.get("mimeType")
    ]
    native_docs = [
        item for item in source_summary if item["mime_type"] == "application/vnd.google-apps.document"
    ]
    portable_docs = [item for item in source_summary if item["mime_type"] in {DOCX_MIME, PDF_MIME}]
    if native_docs:
        return {
            "kind": "document_writeback_decision",
            "mode": "batch_update",
            "selected_mode": "batch_update",
            "planned_method": "gws_docs_documents_batchUpdate",
            "available_methods": ["batch_update"],
            "targets": native_docs,
            "live_update_performed": False,
            "status": "planned_not_executed",
        }
    if portable_docs:
        return {
            "kind": "document_writeback_decision",
            "mode": "versioned_upload_or_convert",
            "selected_mode": "versioned_upload_or_convert",
            "planned_method": "choose_versioned_upload_or_convert_to_google_docs",
            "available_methods": ["versioned_upload", "convert_to_google_docs"],
            "targets": portable_docs,
            "live_update_performed": False,
            "status": "decision_required",
        }
    return {
        "kind": "document_writeback_decision",
        "mode": "no_document_targets",
        "selected_mode": "no_document_targets",
        "planned_method": "none",
        "available_methods": [],
        "targets": [],
        "live_update_performed": False,
        "status": "not_applicable",
    }


def categorize_missing_info(missing_info: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    categories = {
        "para_firma": [],
        "para_entrega_cliente": [],
        "para_revision_interna": [],
        "no_bloqueante": [],
    }
    for item in missing_info:
        if not isinstance(item, dict):
            continue
        taxonomy = str(item.get("taxonomy") or "para_revision_interna")
        category = taxonomy if taxonomy in categories else "para_revision_interna"
        if taxonomy == "para_avanzar":
            category = "para_revision_interna"
        categories[category].append(item)
    return categories


def render_missing_info_request(
    client: dict[str, Any],
    matter: dict[str, Any],
    categories: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# Solicitud de faltantes",
        "",
        f"Cliente: {client.get('name') or client.get('id') or 'Cliente por confirmar'}",
        f"Asunto: {matter.get('id') or 'Asunto por confirmar'}",
        "",
        "Esta solicitud separa datos faltantes detectados en las fuentes. No se inventan hechos reales del cliente.",
    ]
    labels = {
        "para_firma": "Para firma",
        "para_entrega_cliente": "Para entrega cliente",
        "para_revision_interna": "Para revision interna",
        "no_bloqueante": "No bloqueante",
    }
    for category, label in labels.items():
        lines.extend(["", f"## {label}"])
        items = categories[category]
        if not items:
            lines.append("- Sin faltantes detectados.")
            continue
        for item in items:
            field = item.get("field") or "dato por confirmar"
            reason = item.get("reason") or "Fuente no suficiente."
            lines.append(f"- {field}: {reason}")
    lines.extend(
        [
            "",
            "## Regla de uso",
            "- Pedir el dato al cliente o a the lawyer con fuente verificable.",
            "- Mantener placeholder y blocker visible mientras no exista evidencia.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_partner_approval_packet(
    client: dict[str, Any],
    matter: dict[str, Any],
    categories: dict[str, list[dict[str, Any]]],
    required_documents: list[str],
) -> str:
    signature_blocked = bool(categories["para_firma"])
    delivery_blocked = bool(categories["para_entrega_cliente"] or categories["para_firma"])
    lines = [
        "# Paquete de aprobacion del socio",
        "",
        f"Cliente: {client.get('name') or client.get('id') or 'Cliente por confirmar'}",
        f"Asunto: {matter.get('id') or 'Asunto por confirmar'}",
        "",
        "## Decision operativa",
        "- Revision interna puede continuar con fuentes existentes y placeholders visibles.",
        f"- Entrega cliente: {'bloqueada por faltantes' if delivery_blocked else 'puede prepararse para aprobacion'}." ,
        f"- Firma: {'bloqueada por datos para firma' if signature_blocked else 'puede pasar a revision de firma'}." ,
        "- Nunca autoriza inventar hechos reales del cliente.",
        "",
        "## Documentos en alcance",
    ]
    lines.extend(f"- {document_type}" for document_type in required_documents or ["Por determinar"])
    lines.extend(["", "## Faltantes resumidos"])
    for category, items in categories.items():
        lines.append(f"- {category}: {len(items)}")
    return "\n".join(lines) + "\n"


def escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def quote_sheet_name(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def column_letter(index: int) -> str:
    result = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


def extract_labeled_value(text: str, label: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(label)}\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return " ".join(match.group(1).strip().split()).strip(" .,:;") or None


def normalize(value: Any) -> str:
    return str(value).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
