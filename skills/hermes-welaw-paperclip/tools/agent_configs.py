"""Build Paperclip Hermes worker configs for We Law."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("config/paperclip-hermes-agents.json")


def load_agent_configs(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_agent_configs(data)
    return data


def validate_agent_configs(data: dict[str, Any]) -> None:
    if data.get("adapterType") != "hermes_local":
        raise ValueError("Top-level adapterType must be hermes_local")
    workers = data.get("workers", [])
    if not workers:
        raise ValueError("At least one worker is required")
    for worker in workers:
        if worker.get("adapterType") != "hermes_local":
            raise ValueError(f"Worker {worker.get('name')} must use hermes_local")
        if not isinstance(worker.get("persistSession"), bool):
            raise ValueError(f"Worker {worker.get('name')} must declare persistSession")
        if not worker.get("promptTemplate"):
            raise ValueError(f"Worker {worker.get('name')} needs promptTemplate")


def workers_by_role(path: str | Path = DEFAULT_CONFIG) -> dict[str, dict[str, Any]]:
    data = load_agent_configs(path)
    return {worker["role"]: worker for worker in data["workers"]}
