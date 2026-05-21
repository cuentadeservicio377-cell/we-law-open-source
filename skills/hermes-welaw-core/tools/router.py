"""Intent routing for Hermes We Law OS."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class Route:
    intent: str
    target_skill: str
    confidence: float
    reasons: tuple[str, ...]


class LegalRouter:
    """Classify Spanish legal-office instructions into We Law skills."""

    ROUTES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        (
            "paquete_documental",
            "hermes-welaw-documentos",
            (
                "paquete",
                "varios documentos",
                "contrato y nda",
                "contrato, nda",
                "convenio +",
                "documentos",
            ),
        ),
        (
            "litigio",
            "hermes-welaw-litigio",
            (
                "demanda",
                "contestacion",
                "juzgado",
                "audiencia",
                "juicio",
                "pruebas",
                "via de apremio",
                "litigio",
            ),
        ),
        (
            "plazo",
            "hermes-welaw-plazos",
            (
                "plazo",
                "vence",
                "vencimiento",
                "recordatorio",
                "agenda",
                "calendario",
                "tarea",
                "seguimiento el",
            ),
        ),
        (
            "cobranza",
            "hermes-welaw-cobranza",
            (
                "anticipo",
                "abono",
                "pago final",
                "cobrar",
                "cobranza",
                "factura",
                "honorarios pagados",
            ),
        ),
        (
            "leccion_aprendida",
            "hermes-welaw-admin",
            (
                "leccion aprendida",
                "aprendizaje",
                "actualiza plantilla",
                "biblioteca",
                "para futuros",
            ),
        ),
        (
            "reporte",
            "hermes-welaw-admin",
            (
                "reporte",
                "resumen semanal",
                "estado del despacho",
                "como vamos",
                "dame el estado",
            ),
        ),
        (
            "contrato",
            "hermes-welaw-documentos",
            (
                "contrato",
                "nda",
                "convenio",
                "prestacion de servicios",
                "aviso de privacidad",
                "terminos y condiciones",
            ),
        ),
        (
            "documento",
            "hermes-welaw-documentos",
            (
                "genera",
                "redacta",
                "haz",
                "borrador",
                "documento",
                "carta",
                "memo",
            ),
        ),
        (
            "nuevo_asunto",
            "hermes-welaw-intake",
            (
                "cliente nuevo",
                "nuevo cliente",
                "nuevo asunto",
                "abre matter",
                "crea matter",
                "fui a ver",
                "me pidio",
                "registr",
            ),
        ),
        (
            "seguimiento",
            "hermes-welaw-expedientes",
            (
                "que falta",
                "que sigue",
                "donde esta",
                "revisa lo que tenemos",
                "expediente",
                "seguimiento",
            ),
        ),
    )

    def route(self, message: str) -> Route:
        normalized = normalize(message)
        scored: list[Route] = []

        for intent, skill, keywords in self.ROUTES:
            matches = tuple(keyword for keyword in keywords if keyword in normalized)
            if not matches:
                continue
            score = min(0.95, 0.42 + (len(matches) * 0.16))
            if re.search(r"\bmat-\d{3,}\b", normalized):
                score += 0.05
            scored.append(Route(intent, skill, min(score, 0.99), matches))

        if not scored:
            return Route("seguimiento", "hermes-welaw-expedientes", 0.25, ("fallback",))

        scored.sort(key=lambda item: priority(item.intent, item.confidence), reverse=True)
        return scored[0]


def normalize(message: str) -> str:
    text = message.lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def priority(intent: str, confidence: float) -> tuple[int, float]:
    order = {
        "paquete_documental": 10,
        "litigio": 9,
        "plazo": 8,
        "cobranza": 8,
        "leccion_aprendida": 8,
        "reporte": 7,
        "contrato": 6,
        "documento": 5,
        "nuevo_asunto": 4,
        "seguimiento": 1,
    }
    return (order.get(intent, 0), confidence)


def route_message(message: str) -> dict[str, object]:
    route = LegalRouter().route(message)
    return {
        "intent": route.intent,
        "target_skill": route.target_skill,
        "confidence": route.confidence,
        "reasons": list(route.reasons),
    }
