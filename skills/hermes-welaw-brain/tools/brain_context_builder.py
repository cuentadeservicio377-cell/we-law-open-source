"""Build BRAIN_CONTEXT and PROCESS_CONTEXT for Hermes/Paperclip work orders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain_gateway import LocalBrainGateway
from entity_resolver import resolve_client_matter
from process_resolver import render_process_context, resolve_processes
from signal_detector import detect_signals


ROOT = Path(__file__).resolve().parents[3]


def build_brain_context(
    text: str,
    *,
    source: str,
    root: str | Path = ROOT,
    active_matter_id: str | None = None,
    active_client_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    resolution = resolve_client_matter(
        text,
        root=root,
        active_matter_id=active_matter_id,
        active_client_id=active_client_id,
    )
    client_id = (resolution.get("client") or {}).get("id") or active_client_id or ""
    matter_id = (resolution.get("matter") or {}).get("id") or active_matter_id or ""
    signals = detect_signals(text, source=source, client_id=client_id, matter_id=matter_id)
    processes = resolve_processes(text, path=root / "config/legal-brain-operating-model.json")
    gateway = LocalBrainGateway(root / "workspace/brain")
    brain_hits = gateway.search(text, limit=8)
    context_markdown = render_brain_context_markdown(
        resolution=resolution,
        signals=signals,
        processes=processes,
        brain_hits=brain_hits,
    )
    confidence = calculate_confidence(resolution, signals, processes)
    return {
        "kind": "BRAIN_CONTEXT",
        "client": resolution.get("client") or {},
        "matter": resolution.get("matter") or {},
        "resolution": resolution,
        "processes": processes,
        "process_context_markdown": render_process_context(processes),
        "signals": signals,
        "brain_hits": brain_hits,
        "open_threads": open_threads(resolution),
        "contradictions": [signal for signal in signals if signal["type"] == "contradiction"],
        "context_markdown": context_markdown,
        "confidence": confidence,
        "requires_question": resolution["requires_question"],
    }


def render_brain_context_markdown(
    *,
    resolution: dict[str, Any],
    signals: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    brain_hits: list[dict[str, Any]],
) -> str:
    client = resolution.get("client") or {}
    matter = resolution.get("matter") or {}
    lines = [
        "BRAIN_CONTEXT",
        "",
        f"Resolution: {resolution['status']}",
        f"Client: {client.get('id', 'unresolved')} — {client.get('label', '')}",
        f"Matter: {matter.get('id', 'unresolved')} — {matter.get('label', '')}",
        "",
        "## Signals",
    ]
    for signal in signals[:10]:
        lines.append(f"- {signal['type']} ({signal['confidence']}): {signal['text'][:180]}")
    lines.extend(["", "## Processes"])
    for process in processes:
        lines.append(f"- {process['id']}: {process['title']}")
    lines.extend(["", "## Brain Hits"])
    for hit in brain_hits[:5]:
        lines.append(f"- {hit['domain']}/{hit['slug']}: {hit['title']}")
    if resolution["requires_question"]:
        lines.extend(["", "## Minimal Question", resolution["question"]])
    return "\n".join(lines)


def open_threads(resolution: dict[str, Any]) -> list[str]:
    threads = []
    if resolution["status"] == "unresolved":
        threads.append("resolver cliente/matter antes de delegar")
    if resolution["status"] == "ambiguous":
        threads.append(resolution["question"])
    return threads


def calculate_confidence(
    resolution: dict[str, Any],
    signals: list[dict[str, Any]],
    processes: list[dict[str, Any]],
) -> float:
    score = 0.2
    if resolution.get("client"):
        score += 0.25
    if resolution.get("matter"):
        score += 0.25
    if signals:
        score += 0.15
    if processes:
        score += 0.15
    if resolution["status"] == "ambiguous":
        score -= 0.2
    return max(0.0, min(1.0, round(score, 2)))


def dump_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)
