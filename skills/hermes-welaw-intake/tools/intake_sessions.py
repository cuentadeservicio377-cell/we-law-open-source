"""Partial intake sessions for We Law."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE = ROOT / "data/intake_sessions.json"

REQUIRED_FIELDS = {
    "client_name": "¿Cómo se llama el cliente?",
    "matter_description": "¿Qué necesita que hagamos?",
    "matter_type": "¿Qué tipo de asunto es: contractual, litigio, corporativo, compliance u otro?",
}

SIGNATURE_FIELDS = {
    "client_rfc": "¿Cuál es el RFC del cliente?",
    "client_address": "¿Cuál es el domicilio para firma?",
    "signer_name": "¿Quién firmará por el cliente?",
}

MATTER_TYPE_PACKS = {
    "contractual": {
        "blocks_drafting": {
            "counterparty_name": "¿Quién es la contraparte?",
            "commercial_terms": "¿Cuáles son los términos comerciales principales?",
        },
        "blocks_filing": {},
    },
    "litigation": {
        "blocks_drafting": {
            "claims_summary": "¿Cuál es la pretensión o defensa principal?",
            "evidence_summary": "¿Qué pruebas o documentos base existen?",
        },
        "blocks_filing": {
            "court": "¿En qué juzgado o autoridad se tramita?",
            "filing_deadline": "¿Cuál es la fecha límite procesal?",
        },
    },
    "compliance": {
        "blocks_drafting": {
            "regulated_activity": "¿Qué actividad o producto debemos revisar?",
            "data_categories": "¿Qué datos o riesgos regulatorios están involucrados?",
        },
        "blocks_filing": {},
    },
    "corporate": {
        "blocks_drafting": {
            "entity_name": "¿Cuál es la sociedad o vehículo corporativo?",
            "corporate_action": "¿Qué acto corporativo se necesita?",
        },
        "blocks_filing": {},
    },
    "collection": {
        "blocks_drafting": {
            "debtor_name": "¿Quién es el deudor?",
            "amount_due": "¿Cuál es el monto adeudado?",
        },
        "blocks_filing": {
            "due_date": "¿Desde cuándo es exigible el pago?",
        },
    },
}

MATTER_TYPE_ALIASES = {
    "litigio": "litigation",
    "litigio_civil": "litigation",
    "laboral": "litigation",
    "contractual": "contractual",
    "contratos": "contractual",
    "corporativo": "corporate",
    "corporate": "corporate",
    "compliance": "compliance",
    "cumplimiento": "compliance",
    "cobranza": "collection",
    "collection": "collection",
}


@dataclass
class IntakeSessionResult:
    session: dict[str, Any]

    def render(self) -> str:
        missing = ", ".join(self.session["missing"]) if self.session["missing"] else "ninguno"
        questions = "\n".join(f"- {item}" for item in self.session["next_questions"]) or "- Ninguna"
        return "\n".join(
            [
                "INTAKE PARCIAL",
                f"Sesion: {self.session['id']}",
                f"Estado: {self.session['status']}",
                f"Faltantes: {missing}",
                "Siguientes preguntas:",
                questions,
            ]
        )


class IntakeSessionStore:
    def __init__(self, path: str | Path = DEFAULT_STORE):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"sessions": [], "next_id": 1}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def create(self, facts: dict[str, Any], source: str = "telegram") -> IntakeSessionResult:
        data = self.load()
        session = {
            "id": f"INTAKE-{data.get('next_id', 1):03d}",
            "status": "draft",
            "source": source,
            "client_id": facts.get("client_id"),
            "matter_id": facts.get("matter_id"),
            "collected": clean_facts(facts),
            "missing": [],
            "next_questions": [],
            "history": [{"event": "created", "timestamp": now(), "summary": "intake session created"}],
        }
        refresh_status(session)
        data["sessions"].append(session)
        data["next_id"] = data.get("next_id", 1) + 1
        self.save(data)
        return IntakeSessionResult(session)

    def merge(self, session_id: str, facts: dict[str, Any]) -> IntakeSessionResult:
        data = self.load()
        for session in data["sessions"]:
            if session["id"] == session_id:
                session["collected"].update(clean_facts(facts))
                session["history"].append({"event": "merged", "timestamp": now(), "fields": sorted(clean_facts(facts))})
                refresh_status(session)
                self.save(data)
                return IntakeSessionResult(session)
        raise KeyError(f"Intake session not found: {session_id}")

    def list_open(self) -> list[dict[str, Any]]:
        return [item for item in self.load()["sessions"] if item["status"] not in {"converted", "cancelled"}]


def clean_facts(facts: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in facts.items() if value not in (None, "")}


def refresh_status(session: dict[str, Any]) -> None:
    collected = session.get("collected", {})
    matter_type = canonical_matter_type(str(collected.get("matter_type", "")))
    pack = MATTER_TYPE_PACKS.get(matter_type, MATTER_TYPE_PACKS["contractual"])
    grouped = {
        "can_start": [key for key in REQUIRED_FIELDS if not collected.get(key)],
        "blocks_drafting": [key for key in pack["blocks_drafting"] if not collected.get(key)],
        "blocks_filing": [key for key in pack["blocks_filing"] if not collected.get(key)],
        "blocks_signature": [key for key in SIGNATURE_FIELDS if not collected.get(key)],
    }
    session["missing_by_urgency"] = grouped
    session["missing"] = flatten_missing(grouped)
    session["next_questions"] = next_questions(grouped, matter_type)
    if grouped["can_start"]:
        session["status"] = "needs_info"
    else:
        session["status"] = "ready_for_matter"


def question_for(key: str) -> str:
    for questions in [REQUIRED_FIELDS, SIGNATURE_FIELDS]:
        if key in questions:
            return questions[key]
    for pack in MATTER_TYPE_PACKS.values():
        for group in ["blocks_drafting", "blocks_filing"]:
            if key in pack[group]:
                return pack[group][key]
    return f"Falta {key}"


def next_questions(grouped: dict[str, list[str]], matter_type: str) -> list[str]:
    if grouped["can_start"]:
        fields = grouped["can_start"][:3]
    else:
        fields = (
            grouped["blocks_drafting"][:2]
            + grouped["blocks_filing"][:1]
            + grouped["blocks_signature"][:1]
        )
    return [question_for(field) for field in fields]


def flatten_missing(grouped: dict[str, list[str]]) -> list[str]:
    return (
        grouped["can_start"]
        + grouped["blocks_drafting"]
        + grouped["blocks_filing"]
        + grouped["blocks_signature"]
    )


def canonical_matter_type(value: str) -> str:
    normalized = value.lower().strip()
    return MATTER_TYPE_ALIASES.get(normalized, normalized if normalized in MATTER_TYPE_PACKS else "contractual")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
