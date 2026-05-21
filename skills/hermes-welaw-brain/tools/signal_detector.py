"""Detect legal-brain signals from Telegram, transcripts and Paperclip text."""

from __future__ import annotations

from typing import Any

from brain_gateway import normalize


SIGNAL_KEYWORDS = {
    "document_request": ["contrato", "nda", "aviso", "arco", "terminos", "convenio", "demanda", "pagare"],
    "document_correction": ["correccion", "corregir", "ajustar", "cambiar", "faltaba", "segunda entrega"],
    "deadline": ["plazo", "vence", "vencimiento", "audiencia", "recordatorio", "agenda"],
    "payment": ["anticipo", "abono", "pago", "honorarios", "factura", "cobranza"],
    "approval": ["aprobar", "aprobacion", "firma", "autorizar", "entregar al cliente"],
    "risk": ["riesgo", "problema", "bloquea", "blocker", "incumplimiento", "sensible"],
    "contradiction": ["contradice", "no coincide", "diferente", "inconsistente", "conflicto"],
    "decision": ["decidimos", "se acordo", "acordamos", "instruccion", "pidio"],
    "template_candidate": ["plantilla", "formato", "modelo"],
    "lesson": ["leccion", "aprendizaje", "mejora"],
}


def detect_signals(
    text: str,
    *,
    source: str,
    client_id: str | None = None,
    matter_id: str | None = None,
) -> list[dict[str, Any]]:
    normalized = normalize(text)
    signals: list[dict[str, Any]] = []
    for signal_type, keywords in SIGNAL_KEYWORDS.items():
        matched = [keyword for keyword in keywords if normalize(keyword) in normalized]
        if matched:
            signals.append(
                build_signal(
                    signal_type,
                    text,
                    source=source,
                    confidence=min(0.95, 0.55 + (0.1 * len(matched))),
                    client_id=client_id,
                    matter_id=matter_id,
                    metadata={"matched_keywords": matched},
                )
            )
    if client_id:
        signals.append(build_signal("client_identity", client_id, source=source, confidence=0.9, client_id=client_id, matter_id=matter_id))
    if matter_id:
        signals.append(build_signal("matter_identity", matter_id, source=source, confidence=0.9, client_id=client_id, matter_id=matter_id))
    if not signals and text.strip():
        signals.append(build_signal("fact", text, source=source, confidence=0.45, client_id=client_id, matter_id=matter_id))
    return signals


def build_signal(
    signal_type: str,
    text: str,
    *,
    source: str,
    confidence: float,
    client_id: str | None = None,
    matter_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": signal_type,
        "text": text.strip(),
        "source": source,
        "confidence": round(confidence, 2),
        "client_id": client_id or "",
        "matter_id": matter_id or "",
        "entities": [],
        "metadata": metadata or {},
    }
