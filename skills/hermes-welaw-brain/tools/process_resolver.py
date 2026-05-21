"""Resolve legal processes from text and brain signals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain_gateway import normalize


ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / "config/legal-brain-operating-model.json"


def load_processes(path: str | Path = MODEL_PATH) -> list[dict[str, Any]]:
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(model["processes"])


def resolve_processes(text: str, *, path: str | Path = MODEL_PATH, limit: int = 4) -> list[dict[str, Any]]:
    normalized = normalize(text)
    resolved = []
    for process in load_processes(path):
        triggers = process.get("triggers", [])
        matches = [trigger for trigger in triggers if normalize(trigger) in normalized]
        score = len(matches) * 10
        if process["id"] == "paquete_contractual" and any(token in normalized for token in ["contrato", "nda", "convenio"]):
            score += 8
        if process["id"] == "privacidad_datos" and any(token in normalized for token in ["privacidad", "arco", "datos"]):
            score += 8
        if process["id"] == "software_ip" and any(token in normalized for token in ["software", "repositorio", "cotitularidad"]):
            score += 8
        if score:
            item = dict(process)
            item["score"] = score
            item["matchedTriggers"] = matches
            resolved.append(item)
    return sorted(resolved, key=lambda item: (-item["score"], item["id"]))[:limit]


def render_process_context(processes: list[dict[str, Any]]) -> str:
    lines = ["PROCESS_CONTEXT", ""]
    if not processes:
        return "PROCESS_CONTEXT\n\nNo process resolved. Hermes Director must classify before delegating."
    for process in processes:
        lines.extend(
            [
                f"## {process['id']} — {process['title']}",
                f"Score: {process.get('score', 0)}",
                f"Roles: {', '.join(process.get('requiredRoles', []))}",
                f"Artifacts: {', '.join(process.get('requiredArtifacts', []))}",
                f"Triggers: {', '.join(process.get('matchedTriggers', [])) or 'sin trigger directo'}",
                "",
            ]
        )
    return "\n".join(lines).strip()
