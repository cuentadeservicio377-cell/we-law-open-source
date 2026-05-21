"""Per-client memory for Hermes We Law OS."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MEMORY_ROOT = ROOT / "data/client_memory"


class ClientMemoryStore:
    def __init__(self, root: str | Path = DEFAULT_MEMORY_ROOT):
        self.root = Path(root)

    def path_for(self, client_id: str) -> Path:
        return self.root / f"{client_id}.json"

    def load(self, client_id: str, client_name: str = "") -> dict[str, Any]:
        path = self.path_for(client_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "client_id": client_id,
            "client_name": client_name,
            "facts": [],
            "preferences": [],
            "risks": [],
            "matter_ids": [],
            "document_notes": [],
            "interaction_history": [],
            "updated_at": now(),
        }

    def save(self, memory: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        memory["updated_at"] = now()
        self.path_for(memory["client_id"]).write_text(
            json.dumps(memory, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def add(
        self,
        client_id: str,
        client_name: str = "",
        facts: list[str] | None = None,
        preferences: list[str] | None = None,
        risks: list[str] | None = None,
        matter_id: str | None = None,
        document_note: str | None = None,
        event: str = "update",
        summary: str = "",
    ) -> dict[str, Any]:
        memory = self.load(client_id, client_name)
        if client_name and not memory.get("client_name"):
            memory["client_name"] = client_name
        extend_unique(memory, "facts", facts or [])
        extend_unique(memory, "preferences", preferences or [])
        extend_unique(memory, "risks", risks or [])
        if matter_id:
            extend_unique(memory, "matter_ids", [matter_id])
        if document_note:
            extend_unique(memory, "document_notes", [document_note])
        memory.setdefault("interaction_history", []).append(
            {"event": event, "summary": summary, "timestamp": now()}
        )
        self.save(memory)
        return memory

    def render_for_context(self, client_id: str, client_name: str = "") -> str:
        memory = self.load(client_id, client_name)
        return "\n".join(
            [
                "MEMORIA CLIENTE",
                f"Cliente: {memory['client_id']} / {memory.get('client_name', '')}",
                f"Hechos: {join_items(memory.get('facts', []))}",
                f"Preferencias: {join_items(memory.get('preferences', []))}",
                f"Riesgos: {join_items(memory.get('risks', []))}",
                f"Matters: {join_items(memory.get('matter_ids', []))}",
                f"Notas documentos: {join_items(memory.get('document_notes', []))}",
            ]
        )


def extend_unique(memory: dict[str, Any], key: str, values: list[str]) -> None:
    existing = list(memory.setdefault(key, []))
    for value in values:
        if value and value not in existing:
            existing.append(value)
    memory[key] = existing


def join_items(items: list[str]) -> str:
    return ", ".join(items) if items else "ninguno"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
