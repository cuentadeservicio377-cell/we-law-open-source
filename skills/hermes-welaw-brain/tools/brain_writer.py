"""Write validated legal brain pages and update proposals."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from brain_gateway import LocalBrainGateway


def write_client_matter_pages(
    *,
    brain_root: str | Path,
    client: dict[str, Any],
    matter: dict[str, Any],
    signals: list[dict[str, Any]],
    source: str,
) -> dict[str, Any]:
    gateway = LocalBrainGateway(brain_root)
    client_id = str(client.get("id") or client.get("client_id"))
    client_name = str(client.get("nombre") or client.get("client_name") or client_id)
    matter_id = str(matter.get("id") or matter.get("matter_id"))
    matter_title = str(matter.get("descripcion") or matter_id)

    client_path = gateway.write_page(
        "clients",
        client_id,
        title=f"{client_id} - {client_name}",
        compiled_truth=render_compiled_truth("Cliente", client_name, signals),
        frontmatter={"client_id": client_id, "canonical_name": client_name, "status": client.get("estado", "activo")},
        timeline=timeline_from_signals(signals, source),
    )
    matter_path = gateway.write_page(
        "matters",
        matter_id,
        title=f"{matter_id} - {matter_title}",
        compiled_truth=render_compiled_truth("Matter", matter_title, signals),
        frontmatter={"matter_id": matter_id, "client_id": client_id, "status": matter.get("estado", "activo"), "phase": matter.get("fase", "")},
        timeline=timeline_from_signals(signals, source),
    )
    return {"client_page": str(client_path), "matter_page": str(matter_path)}


def build_update_proposal(
    *,
    proposed_by: str,
    client_id: str,
    matter_id: str,
    signals: list[dict[str, Any]],
    source_artifacts: list[str],
) -> dict[str, Any]:
    facts = [
        {"text": signal["text"], "source": signal["source"], "confidence": signal["confidence"]}
        for signal in signals
        if signal["type"] in {"fact", "document_request", "decision", "risk"}
    ]
    contradictions = [
        {"text": signal["text"], "source": signal["source"], "confidence": signal["confidence"]}
        for signal in signals
        if signal["type"] == "contradiction"
    ]
    timeline_entries = [
        {"date": str(date.today()), "source": signal["source"], "summary": f"{signal['type']}: {signal['text'][:180]}"}
        for signal in signals
    ]
    return {
        "kind": "BRAIN_UPDATE_PROPOSAL",
        "proposed_by": proposed_by,
        "client_id": client_id,
        "matter_id": matter_id,
        "facts": facts,
        "timeline_entries": timeline_entries,
        "contradictions": contradictions,
        "missing_info": [],
        "source_artifacts": source_artifacts,
        "requires_review": True,
    }


def render_compiled_truth(kind: str, title: str, signals: list[dict[str, Any]]) -> str:
    lines = [f"{kind}: {title}", "", "Hechos y señales actuales:"]
    for signal in signals[:12]:
        lines.append(f"- {signal['type']}: {signal['text'][:220]} [Source: {signal['source']}]")
    return "\n".join(lines)


def timeline_from_signals(signals: list[dict[str, Any]], source: str) -> list[dict[str, str]]:
    return [
        {"date": str(date.today()), "source": signal.get("source") or source, "summary": f"{signal['type']}: {signal['text'][:180]}"}
        for signal in signals
    ] or [{"date": str(date.today()), "source": source, "summary": "Brain page created."}]
