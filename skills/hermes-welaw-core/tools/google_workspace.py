"""Google Workspace adapter contract for Hermes We Law OS."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_ROOT_NAME = "We Law S.C."
DEFAULT_FOLDERS = ["Clientes", "Asuntos", "Plantillas", "Biblioteca"]
DEFAULT_SHEETS = ["Clientes", "Asuntos", "Finanzas"]
MATTER_FOLDER_TEMPLATE = [
    "00-Insumos crudos",
    "01-Transcripciones",
    "02-Expediente vivo",
    "03-Matriz legal",
    "04-Documentos en trabajo",
    "05-Revision senior",
    "06-Entregables al Cliente",
    "07-Archivo",
]
CONTROL_MASTER_TABLES = [
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
SECRET_ENV_KEYS = [
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "GOOGLE_REFRESH_TOKEN",
    "GOOGLE_CLIENT_SECRET",
    "WORKSPACE_MCP_ENV",
]

VALID_CREDENTIAL_KEYS = {
    "client_id",
    "client_secret",
    "refresh_token",
    "token",
    "token_uri",
}


def _default_workspace_credential_files() -> list[Path]:
    candidate_paths: list[Path] = []
    active_profile_path = Path.home() / ".hermes" / "active_profile"
    if active_profile_path.exists():
        active_profile = active_profile_path.read_text().strip()
        if active_profile:
            candidate_paths.append(Path.home() / ".hermes" / "profiles" / active_profile / "google_token.json")
    mcp_credentials = Path.home() / ".google_workspace_mcp" / "credentials"
    if mcp_credentials.exists():
        candidate_paths.extend(sorted(mcp_credentials.glob("*.json")))
    candidate_paths.append(Path.home() / ".config" / "gws" / "token_cache.json")
    return candidate_paths


class WorkspaceWriteBlocked(RuntimeError):
    """Raised when a Google Workspace write is attempted without approval."""


class WorkspaceReadError(RuntimeError):
    """Raised when a fake or real workspace read cannot be completed."""


@dataclass
class FakeWorkspaceAdapter:
    folders: dict[str, dict[str, Any]] = field(default_factory=dict)
    docs: dict[str, str] = field(default_factory=dict)

    def read_folder_metadata(self, folder_id: str) -> dict[str, Any]:
        if folder_id not in self.folders:
            raise WorkspaceReadError(f"folder not found: {folder_id}")
        return dict(self.folders[folder_id])

    def export_doc_text(self, doc_id: str) -> str:
        if doc_id not in self.docs:
            raise WorkspaceReadError(f"doc not found: {doc_id}")
        return self.docs[doc_id]


def discover_workspace_credentials(
    *,
    env: dict[str, str] | None = None,
    candidate_files: list[str | Path] | None = None,
) -> dict[str, Any]:
    active_env = env if env is not None else dict(os.environ)
    sources: list[dict[str, Any]] = []
    for key in SECRET_ENV_KEYS:
        value = active_env.get(key)
        if not value:
            continue
        sources.append(
            {
                "type": "env",
                "name": key,
                "configured": True,
                "value": "<redacted>",
                "path": value if key.endswith(("FILE", "CREDENTIALS", "ENV")) else None,
            }
        )

    for path_value in (candidate_files or _default_workspace_credential_files()):
        path = Path(path_value)
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if not VALID_CREDENTIAL_KEYS.intersection(payload.keys()):
            continue
        sources.append({"type": "file", "path": str(path), "configured": True, "value": "<redacted>"})

    return {
        "configured": bool(sources),
        "sources": sources,
        "preferred_adapter": "workspace_mcp" if active_env.get("WORKSPACE_MCP_ENV") else "gws_cli",
    }


def build_workspace_topology_manifest(
    *,
    root_name: str = DEFAULT_ROOT_NAME,
    dry_run: bool = True,
    approved: bool = False,
) -> dict[str, Any]:
    return {
        "kind": "welaw_google_workspace_manifest",
        "dry_run": dry_run,
        "root": {"name": root_name},
        "folders": [{"name": name, "parent": root_name} for name in DEFAULT_FOLDERS],
        "sheets": [{"name": name, "tabs": default_tabs(name)} for name in DEFAULT_SHEETS],
        "matter_folder_template": MATTER_FOLDER_TEMPLATE,
        "control_master_tables": CONTROL_MASTER_TABLES,
        "write_gate": {
            "approved": approved,
            "mode": "dry_run" if dry_run else "write",
            "requirement": "explicit user approval and configured credentials",
        },
    }


def assert_write_allowed(*, approved: bool, dry_run: bool) -> None:
    if dry_run:
        return
    if not approved:
        raise WorkspaceWriteBlocked("Google Workspace write requires explicit approval")


def read_drive_folder_metadata(adapter: Any, folder_id: str) -> dict[str, Any]:
    return adapter.read_folder_metadata(folder_id)


def export_google_doc_text(adapter: Any, doc_id: str) -> str:
    return adapter.export_doc_text(doc_id)


def default_tabs(sheet_name: str) -> list[str]:
    if sheet_name == "Clientes":
        return ["Clientes", "Contactos", "KYC"]
    if sheet_name == "Asuntos":
        return ["Asuntos", "Plazos", "Entregables"]
    if sheet_name == "Finanzas":
        return ["Pagos", "Honorarios", "Cobranza"]
    return ["Hoja1"]
