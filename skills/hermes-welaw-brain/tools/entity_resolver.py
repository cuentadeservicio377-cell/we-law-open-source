"""Client and matter resolver for the We Law Legal Brain."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from brain_gateway import LocalBrainGateway, normalize


ROOT = Path(__file__).resolve().parents[3]


@dataclass
class ResolutionCandidate:
    kind: str
    id: str
    label: str
    score: int
    reasons: list[str]
    data: dict[str, Any]


def resolve_client_matter(
    text: str,
    *,
    root: str | Path = ROOT,
    active_matter_id: str | None = None,
    active_client_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    clients = read_json(root / "data/clients.json", [])
    matters = read_json(root / "data/matters.json", [])
    memories = read_client_memories(root / "data/client_memory")
    gateway = LocalBrainGateway(root / "workspace/brain")

    client_candidates = score_clients(text, clients, memories, active_client_id=active_client_id)
    matter_candidates = score_matters(text, matters, client_candidates, active_matter_id=active_matter_id)

    brain_hits = gateway.search(text, domains=["clients", "matters"], limit=5)
    for hit in brain_hits:
        if hit["domain"] == "clients":
            client_candidates.append(
                ResolutionCandidate("client", hit["slug"], hit["title"], hit["score"], ["brain_search"], {"brain_path": hit["path"]})
            )
        if hit["domain"] == "matters":
            matter_candidates.append(
                ResolutionCandidate("matter", hit["slug"], hit["title"], hit["score"], ["brain_search"], {"brain_path": hit["path"]})
            )

    best_client = choose(client_candidates)
    best_matter = choose(matter_candidates)
    status = "resolved"
    if is_ambiguous(client_candidates) or is_ambiguous(matter_candidates):
        status = "ambiguous"
    if not best_client and not best_matter:
        status = "unresolved"

    return {
        "status": status,
        "client": candidate_to_dict(best_client),
        "matter": candidate_to_dict(best_matter),
        "client_candidates": [candidate_to_dict(item) for item in sorted_candidates(client_candidates)],
        "matter_candidates": [candidate_to_dict(item) for item in sorted_candidates(matter_candidates)],
        "requires_question": status == "ambiguous",
        "question": build_question(client_candidates, matter_candidates) if status == "ambiguous" else "",
    }


def score_clients(
    text: str,
    clients: list[dict[str, Any]],
    memories: dict[str, dict[str, Any]],
    *,
    active_client_id: str | None = None,
) -> list[ResolutionCandidate]:
    normalized = normalize(text)
    candidates = []
    explicit_ids = set(re.findall(r"\bCLI-\d{3,}\b", text, flags=re.IGNORECASE))
    for client in clients:
        score = 0
        reasons: list[str] = []
        client_id = str(client.get("id", ""))
        names = [str(client.get("nombre", "")), str(client.get("empresa", "")), str(client.get("contacto", ""))]
        memory = memories.get(client_id, {})
        names.extend(memory.get("aliases", []))
        if client_id in explicit_ids:
            score += 100
            reasons.append("explicit_client_id")
        if active_client_id and active_client_id == client_id:
            score += 20
            reasons.append("active_client")
        for name in names:
            if name and normalize(name) in normalized:
                score += 35 if name in [client.get("nombre"), client.get("empresa")] else 12
                reasons.append(f"name_match:{name}")
            elif name:
                shared_tokens = [token for token in re.split(r"\W+", normalize(name)) if len(token) >= 5 and token in normalized]
                if shared_tokens:
                    score += 20
                    reasons.append(f"partial_name_match:{'/'.join(shared_tokens)}")
        if score:
            candidates.append(
                ResolutionCandidate("client", client_id, str(client.get("nombre", client_id)), score, reasons, client)
            )
    if active_client_id and not any(candidate.id == active_client_id for candidate in candidates):
        candidates.append(
            ResolutionCandidate(
                "client",
                active_client_id,
                active_client_id,
                90,
                ["active_client_unregistered"],
                {"id": active_client_id, "estado": "pending_brain_registration"},
            )
        )
    return candidates


def score_matters(
    text: str,
    matters: list[dict[str, Any]],
    client_candidates: list[ResolutionCandidate],
    *,
    active_matter_id: str | None = None,
) -> list[ResolutionCandidate]:
    normalized = normalize(text)
    explicit_ids = set(re.findall(r"\bMAT-\d{3,}\b", text, flags=re.IGNORECASE))
    candidate_client_ids = {candidate.id for candidate in client_candidates if candidate.score >= 20}
    candidates = []
    for matter in matters:
        score = 0
        reasons: list[str] = []
        matter_id = str(matter.get("id", ""))
        if matter_id in explicit_ids:
            score += 100
            reasons.append("explicit_matter_id")
        if active_matter_id and active_matter_id == matter_id:
            score += 25
            reasons.append("active_matter")
        if matter.get("client_id") in candidate_client_ids:
            score += 20
            reasons.append("client_link")
        for field in ["cliente", "tipo", "descripcion", "fase", "drive_path"]:
            value = str(matter.get(field, ""))
            if value and normalize(value) in normalized:
                score += 25 if field in ["cliente", "descripcion"] else 8
                reasons.append(f"matter_field:{field}")
        if score:
            candidates.append(
                ResolutionCandidate("matter", matter_id, str(matter.get("descripcion", matter_id)), score, reasons, matter)
            )
    if active_matter_id and not any(candidate.id == active_matter_id for candidate in candidates):
        candidates.append(
            ResolutionCandidate(
                "matter",
                active_matter_id,
                active_matter_id,
                35,
                ["active_matter_unregistered"],
                {"id": active_matter_id, "estado": "pending_brain_registration"},
            )
        )
    return candidates


def choose(candidates: list[ResolutionCandidate]) -> ResolutionCandidate | None:
    ordered = sorted_candidates(candidates)
    return ordered[0] if ordered else None


def sorted_candidates(candidates: list[ResolutionCandidate]) -> list[ResolutionCandidate]:
    return sorted(candidates, key=lambda item: (-item.score, item.id))


def is_ambiguous(candidates: list[ResolutionCandidate]) -> bool:
    ordered = sorted_candidates(candidates)
    return len(ordered) >= 2 and ordered[0].score == ordered[1].score and ordered[0].score >= 20


def candidate_to_dict(candidate: ResolutionCandidate | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    return {
        "kind": candidate.kind,
        "id": candidate.id,
        "label": candidate.label,
        "score": candidate.score,
        "reasons": candidate.reasons,
        "data": candidate.data,
    }


def build_question(
    client_candidates: list[ResolutionCandidate],
    matter_candidates: list[ResolutionCandidate],
) -> str:
    if is_ambiguous(matter_candidates):
        labels = ", ".join(f"{item.id} ({item.label})" for item in sorted_candidates(matter_candidates)[:3])
        return f"¿A qué matter te refieres: {labels}?"
    labels = ", ".join(f"{item.id} ({item.label})" for item in sorted_candidates(client_candidates)[:3])
    return f"¿A qué cliente te refieres: {labels}?"


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def read_client_memories(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    memories = {}
    for file in path.glob("*.json"):
        data = read_json(file, {})
        client_id = data.get("client_id") or file.stem
        memories[str(client_id)] = data
    return memories
