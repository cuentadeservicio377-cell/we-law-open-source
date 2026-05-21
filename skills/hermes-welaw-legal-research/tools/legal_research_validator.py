"""Deterministic legal-research validator for We Law packets."""

from __future__ import annotations

from typing import Any


LEGAL_TOPIC_KEYWORDS = {
    "privacy_lfpdppp": ["lfpdppp", "privacidad", "datos personales", "arco"],
    "software_contracts": ["software", "desarrollo", "saas", "repositorio"],
    "ip": ["propiedad intelectual", "cotitularidad", "impi", "obra por encargo"],
    "confidentiality": ["nda", "confidencialidad"],
    "consumer_terms": ["términos", "terminos", "condiciones", "venta"],
}


def validate_legal_research_packet(packet: dict[str, Any]) -> dict[str, Any]:
    text = str(packet.get("text") or packet.get("content") or "").lower()
    topics = [
        topic
        for topic, keywords in LEGAL_TOPIC_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    return {
        "kind": "legal_research_validation",
        "status": "passed" if topics else "needs_review",
        "legal_topics": topics,
        "checks": {
            "has_legal_basis_topic": bool(topics),
            "requires_human_citation_review": True,
        },
        "required_artifacts": ["LEGAL_BASIS_MEMO.md", "DOCUMENT_REQUIREMENTS.json", "RISK_MATRIX.md"],
    }
