"""Folder planning for We Law client and matter workspaces."""

from __future__ import annotations

from typing import Any


CLIENT_FOLDERS = [
    "00-Cliente",
    "01-Matters",
    "02-Documentos fundacionales",
    "03-Historial",
]

MATTER_FOLDERS = [
    "00-Insumos crudos",
    "01-Expediente vivo",
    "02-Documentos en trabajo",
    "03-Revision y aprobaciones",
    "04-Versiones aprobadas",
    "05-Anexos y evidencia",
    "06-Cobranza",
    "07-Cierre",
]

LITIGATION_EXTRA = [
    "02-Demanda inicial",
    "03-Estrategia de litigio",
    "04-Anexos y evidencia",
    "05-Versiones aprobadas",
]


def plan_client_matter_folders(
    client: dict[str, Any],
    matter: dict[str, Any],
) -> dict[str, Any]:
    client_root = f"Clientes/{client['id']} - {client['nombre']}"
    matter_root = f"{client_root}/01-Matters/{matter['id']} - {matter_title(matter)}"

    matter_folders = LITIGATION_EXTRA if is_litigation(matter) else MATTER_FOLDERS

    return {
        "client_root": client_root,
        "matter_root": matter_root,
        "client_folders": [f"{client_root}/{name}" for name in CLIENT_FOLDERS],
        "matter_folders": [f"{matter_root}/{name}" for name in matter_folders],
        "litigation": is_litigation(matter),
    }


def is_litigation(matter: dict[str, Any]) -> bool:
    value = f"{matter.get('tipo', '')} {matter.get('descripcion', '')}".lower()
    return any(word in value for word in ["litigio", "demanda", "juicio", "juzgado"])


def matter_title(matter: dict[str, Any]) -> str:
    raw = matter.get("nombre") or matter.get("descripcion") or "Asunto"
    return " ".join(str(raw).split()[:5]).title()
