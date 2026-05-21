"""Legal trigger catalog for Telegram and Paperclip routing."""

from __future__ import annotations

import json
from pathlib import Path
import re
from string import Formatter
from typing import Any

from firm_model import load_firm_model


DEFAULT_CATALOG_PATH = Path("config/legal-trigger-catalog.json")
DEFAULT_FIRM_MODEL_PATH = Path("config/firm-operating-model.json")
REQUIRED_TRIGGER_FIELDS = {
    "id",
    "targetRole",
    "requiredFields",
    "optionalFields",
    "issueTitlePattern",
    "eventType",
    "approvalType",
    "allowedArtifacts",
    "completionGate",
    "examples",
}


class TriggerCatalogError(ValueError):
    """Raised when a trigger catalog or trigger command is malformed."""


def load_trigger_catalog(path: str | Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise TriggerCatalogError(f"Legal trigger catalog not found: {catalog_path}")
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TriggerCatalogError(f"Invalid legal trigger catalog JSON: {catalog_path}") from exc
    validate_trigger_catalog(catalog)
    return catalog


def validate_trigger_catalog(catalog: dict[str, Any]) -> None:
    triggers = catalog.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        raise TriggerCatalogError("triggers must be a non-empty list")

    firm_model = load_firm_model(DEFAULT_FIRM_MODEL_PATH)
    roles = firm_model["roles"]
    approval_types = set(firm_model["approvalTypes"])
    seen: set[str] = set()

    for trigger in triggers:
        if not isinstance(trigger, dict):
            raise TriggerCatalogError("each trigger must be an object")
        missing = sorted(REQUIRED_TRIGGER_FIELDS - set(trigger))
        if missing:
            raise TriggerCatalogError(f"trigger missing fields: {', '.join(missing)}")
        trigger_id = str(trigger["id"])
        if trigger_id in seen:
            raise TriggerCatalogError(f"duplicate trigger id: {trigger_id}")
        seen.add(trigger_id)
        if trigger["targetRole"] not in roles:
            raise TriggerCatalogError(f"trigger {trigger_id} targets unknown role {trigger['targetRole']}")
        approval = trigger.get("approvalType")
        if approval is not None and approval not in approval_types:
            raise TriggerCatalogError(f"trigger {trigger_id} has unknown approval type {approval}")
        for key in ["requiredFields", "optionalFields", "allowedArtifacts", "examples"]:
            values = trigger.get(key)
            if not isinstance(values, list) or (key != "optionalFields" and not values):
                raise TriggerCatalogError(f"trigger {trigger_id} {key} must be a list")
        if not str(trigger.get("completionGate", "")).strip():
            raise TriggerCatalogError(f"trigger {trigger_id} needs completionGate")
        _validate_pattern_fields(trigger)


def parse_structured_trigger(text: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    active_catalog = catalog or load_trigger_catalog()
    parts = text.strip().split()
    if not parts:
        raise TriggerCatalogError("empty trigger command")

    trigger = trigger_by_id(active_catalog, normalize(parts[0]))
    fields = parse_key_value_fields(parts[1:])
    matter_id = extract_matter_id(text)
    if matter_id:
        fields.setdefault("matterId", matter_id)

    if trigger["id"] == "generar_documento" and "documentType" not in fields:
        after_colon = text.split(":", 1)[1].strip() if ":" in text else ""
        if after_colon:
            fields["documentType"] = after_colon.split()[0]

    fill_defaults(trigger, fields, text)
    return build_candidate(trigger, fields, matter_id, source="structured", confidence=0.98)


def normalize_telegram_note(text: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    active_catalog = catalog or load_trigger_catalog()
    normalized = normalize(text)
    matter_id = extract_matter_id(text)
    fields: dict[str, str] = {}
    if matter_id:
        fields["matterId"] = matter_id

    if any(token in normalized for token in ["fui a ver", "cliente nuevo", "nuevo cliente", "nuevo asunto"]):
        trigger_id = "nuevo_asunto"
        fields["clientName"] = extract_client_name(text) or "Cliente por confirmar"
        fields["matterDescription"] = summarize_note(text)
    elif any(token in normalized for token in ["plazo", "vence", "vencimiento", "audiencia"]):
        trigger_id = "plazo_judicial"
        fields["deadlineName"] = "plazo judicial"
    elif "pago final" in normalized or "liquidaron" in normalized or "liquido" in normalized:
        trigger_id = "pago_final_recibido"
    elif "abono" in normalized:
        trigger_id = "abono_recibido"
    elif "anticipo" in normalized:
        trigger_id = "anticipo_recibido"
    elif "cerrar" in normalized or "cierre" in normalized:
        trigger_id = "cerrar_asunto"
    elif "reporte semanal" in normalized:
        trigger_id = "reporte_semanal"
        fields["week"] = "semana_actual"
    elif "reporte" in normalized:
        trigger_id = "reporte_matter"
    elif "leccion aprendida" in normalized or "actualiza plantilla" in normalized:
        trigger_id = "leccion_aprendida"
        fields["topic"] = "por_clasificar"
    elif "paquete" in normalized:
        trigger_id = "generar_paquete"
        fields["packageName"] = "paquete legal"
    elif any(token in normalized for token in ["contrato", "nda", "documento", "redacta", "genera", "aviso de privacidad"]):
        trigger_id = "generar_documento"
        fields["documentType"] = infer_document_type(normalized)
    else:
        trigger_id = "actualizacion" if matter_id else "tarea"
        fields["summary" if trigger_id == "actualizacion" else "task"] = summarize_note(text)

    trigger = trigger_by_id(active_catalog, trigger_id)
    fill_defaults(trigger, fields, text)
    return build_candidate(trigger, fields, matter_id, source="telegram_note", confidence=0.82 if matter_id else 0.66)


def build_issue_title(trigger: dict[str, Any], *, matter_id: str | None = None, fields: dict[str, Any] | None = None) -> str:
    values = {str(key): str(value) for key, value in (fields or {}).items()}
    if matter_id:
        values["matterId"] = matter_id
    values.setdefault("matterId", "MAT-PENDIENTE")
    values.setdefault("clientName", "Cliente por confirmar")
    values.setdefault("matterDescription", "asunto por clasificar")
    values.setdefault("documentType", "documento")
    values.setdefault("packageName", "paquete")
    values.setdefault("task", "tarea")
    values.setdefault("deadlineName", "plazo")
    values.setdefault("summary", "actualizacion")
    values.setdefault("week", "semana_actual")
    values.setdefault("topic", "tema")
    return SafeFormatter().format(str(trigger["issueTitlePattern"]), **values).strip()


def trigger_by_id(catalog: dict[str, Any], trigger_id: str) -> dict[str, Any]:
    for trigger in catalog["triggers"]:
        if trigger["id"] == trigger_id:
            return trigger
    raise TriggerCatalogError(f"unknown trigger: {trigger_id}")


def build_candidate(
    trigger: dict[str, Any],
    fields: dict[str, Any],
    matter_id: str | None,
    *,
    source: str,
    confidence: float,
) -> dict[str, Any]:
    issue_title = build_issue_title(trigger, matter_id=matter_id, fields=fields)
    return {
        "trigger_id": trigger["id"],
        "target_role": trigger["targetRole"],
        "matter_id": matter_id,
        "fields": fields,
        "issue_title": issue_title,
        "event_type": trigger["eventType"],
        "approval_type": trigger["approvalType"],
        "completion_gate": trigger["completionGate"],
        "source": source,
        "confidence": confidence,
    }


def parse_key_value_fields(parts: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def fill_defaults(trigger: dict[str, Any], fields: dict[str, Any], text: str) -> None:
    for field in trigger["requiredFields"]:
        if field in fields:
            continue
        if field == "matterId":
            fields[field] = extract_matter_id(text) or "MAT-PENDIENTE"
        elif field == "clientName":
            fields[field] = extract_client_name(text) or "Cliente por confirmar"
        elif field == "matterDescription":
            fields[field] = summarize_note(text)
        elif field == "documentType":
            fields[field] = infer_document_type(normalize(text))
        elif field == "deadlineName":
            fields[field] = "plazo judicial"
        elif field == "week":
            fields[field] = "semana_actual"
        elif field == "topic":
            fields[field] = "por_clasificar"
        elif field == "packageName":
            fields[field] = "paquete legal"
        elif field == "task":
            fields[field] = summarize_note(text)
        elif field == "summary":
            fields[field] = summarize_note(text)
        else:
            fields[field] = "por_confirmar"


def extract_matter_id(text: str) -> str | None:
    match = re.search(r"\bMAT-\d{3,}\b", text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_client_name(text: str) -> str | None:
    patterns = [
        r"(?:fui a ver a|vi a|me reuni con|reunion con|cliente nuevo|nuevo cliente)\s+(.+?)(?:[.,;]| quiere\b| necesita\b| me pid[ií]o\b| pide\b| solicita\b| para\b|$)",
        r"(?:cliente|prospecto)\s+(.+?)(?:[.,;]| quiere\b| necesita\b| me pid[ií]o\b| pide\b| solicita\b| para\b|$)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).strip().split())
            return value.strip(" .,:;") or None
    return None


def infer_document_type(normalized: str) -> str:
    if "nda" in normalized or "confidencialidad" in normalized:
        return "nda"
    if "aviso de privacidad" in normalized:
        return "aviso_privacidad"
    if "terminos" in normalized:
        return "terminos_condiciones"
    if "demanda" in normalized:
        return "demanda_inicial"
    if "contrato" in normalized:
        return "contrato"
    return "documento"


def summarize_note(text: str) -> str:
    clean = " ".join(text.strip().split())
    return clean[:96] if clean else "por confirmar"


def normalize(value: str) -> str:
    text = value.lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def _validate_pattern_fields(trigger: dict[str, Any]) -> None:
    pattern_fields = {
        name for _, name, _, _ in Formatter().parse(str(trigger["issueTitlePattern"])) if name
    }
    known_fields = set(trigger["requiredFields"]) | set(trigger["optionalFields"]) | {
        "matterId",
        "clientName",
        "matterDescription",
        "documentType",
        "packageName",
        "task",
        "deadlineName",
        "summary",
        "week",
        "topic",
    }
    unknown = sorted(pattern_fields - known_fields)
    if unknown:
        raise TriggerCatalogError(f"trigger {trigger['id']} title pattern has unknown fields: {', '.join(unknown)}")


class SafeFormatter(Formatter):
    def get_value(self, key: Any, args: Any, kwargs: dict[str, Any]) -> Any:
        if isinstance(key, str):
            return kwargs.get(key, "por_confirmar")
        return Formatter.get_value(self, key, args, kwargs)
