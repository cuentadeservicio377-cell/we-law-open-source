"""Transcript intake extraction for Hermes We Law OS."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CORE_TOOLS = ROOT / "skills/hermes-welaw-core/tools"
if str(CORE_TOOLS) not in sys.path:
    sys.path.insert(0, str(CORE_TOOLS))

from legal_knowledge import infer_required_documents, required_reviewers_for_package


SIGNATURE_MISSING_FIELDS = {
    "rfc": "cliente.rfc",
    "domicilio": "cliente.domicilio",
    "representante": "cliente.representante",
    "firmante": "cliente.representante",
}


def build_transcript_intake(transcripts: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_transcripts = normalize_transcripts(transcripts)
    combined_text = "\n".join(item["text"] for item in normalized_transcripts)
    required_documents = infer_required_documents(combined_text)
    data_ledger = extract_data_ledger(normalized_transcripts)

    return {
        "kind": "transcript_intake",
        "source_count": len(normalized_transcripts),
        "client": {
            "name": data_ledger.get("cliente.nombre", {}).get("value", "Cliente por confirmar"),
        },
        "matter": {
            "description": data_ledger.get("matter.descripcion", {}).get("value", "Asunto por clasificar"),
        },
        "required_documents": required_documents,
        "reviewers": required_reviewers_for_package(required_documents),
        "data_ledger": data_ledger,
        "evidence_map": evidence_map_from_ledger(data_ledger),
        "corrections": extract_corrections(normalized_transcripts),
        "missing_info": extract_missing_info(normalized_transcripts, data_ledger),
    }


def normalize_transcripts(transcripts: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, transcript in enumerate(transcripts, start=1):
        source_id = str(transcript.get("id") or f"TRANS-{index:03d}")
        normalized.append(
            {
                "id": source_id,
                "title": str(transcript.get("title") or source_id),
                "text": str(transcript.get("text") or "").strip(),
            }
        )
    return normalized


def extract_data_ledger(transcripts: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    ledger: dict[str, dict[str, Any]] = {}
    for transcript in transcripts:
        text = transcript["text"]
        add_fact(ledger, "cliente.nombre", extract_labeled_value(text, "Cliente"), transcript)
        add_fact(ledger, "matter.descripcion", extract_labeled_value(text, "Proyecto"), transcript)
        add_fact(ledger, "cliente.rfc", extract_labeled_value(text, "RFC"), transcript, confidence=0.95)
        add_fact(ledger, "cliente.domicilio", extract_labeled_value(text, "Domicilio"), transcript, confidence=0.95)
        add_fact(ledger, "cliente.representante", extract_labeled_value(text, "Representante"), transcript, confidence=0.95)
    return ledger


def add_fact(
    ledger: dict[str, dict[str, Any]],
    field: str,
    value: str | None,
    transcript: dict[str, str],
    *,
    confidence: float = 0.86,
) -> None:
    if not value or field in ledger:
        return
    ledger[field] = {
        "value": value,
        "source_id": transcript["id"],
        "source_title": transcript["title"],
        "confidence": confidence,
    }


def extract_labeled_value(text: str, label: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(label)}\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return clean_labeled_value(match.group(1))


def clean_labeled_value(value: str) -> str:
    value = " ".join(value.strip().split())
    value = re.split(r"\.\s+(?:Quiere|Necesita|Solicita|Pide)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = value.strip(" ,:;")
    if value.endswith(".") and not re.search(r"\b(?:S\.A|C\.V|S\.C)\.$", value):
        value = value[:-1]
    return value


def evidence_map_from_ledger(ledger: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        field: [
            {
                "source_id": fact["source_id"],
                "source_title": fact["source_title"],
                "value": fact["value"],
                "confidence": fact["confidence"],
            }
        ]
        for field, fact in ledger.items()
    }


def extract_corrections(transcripts: list[dict[str, str]]) -> list[dict[str, Any]]:
    corrections: list[dict[str, Any]] = []
    for transcript in transcripts:
        for line in transcript["text"].splitlines():
            if "correccion" not in normalize(line) and "corrección" not in line.lower():
                continue
            instruction = line.split(":", 1)[1].strip() if ":" in line else line.strip()
            corrections.append(
                {
                    "source_id": transcript["id"],
                    "source_title": transcript["title"],
                    "instruction": instruction,
                    "target": infer_correction_target(instruction),
                    "status": "pending_application",
                }
            )
    return corrections


def infer_correction_target(instruction: str) -> str:
    normalized = normalize(instruction)
    if "medico" in normalized or "paciente" in normalized:
        return "aviso_privacidad_medicos_pacientes"
    if "desarrollo" in normalized or "software" in normalized or "repositorio" in normalized:
        return "contrato_desarrollo_software"
    if "arco" in normalized:
        return "formato_arco"
    if "nda" in normalized or "confidencialidad" in normalized:
        return "nda"
    return "package"


def extract_missing_info(
    transcripts: list[dict[str, str]],
    ledger: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    combined = normalize("\n".join(item["text"] for item in transcripts))
    for token, field in SIGNATURE_MISSING_FIELDS.items():
        if field in ledger:
            continue
        if token in combined:
            missing.append({"field": field, "taxonomy": "para_firma", "reason": "Mentioned as missing in transcript"})
    return missing


def normalize(value: str) -> str:
    return value.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
