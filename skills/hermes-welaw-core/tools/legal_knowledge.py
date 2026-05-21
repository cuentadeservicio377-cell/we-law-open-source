"""Legal knowledge map for Hermes We Law OS."""

from __future__ import annotations

import json
from pathlib import Path
import unicodedata
from typing import Any

from firm_model import load_firm_model


DEFAULT_KNOWLEDGE_PATH = Path("config/legal-knowledge-map.json")
DEFAULT_FIRM_MODEL_PATH = Path("config/firm-operating-model.json")
REQUIRED_DOCUMENT_FIELDS = {
    "title",
    "area",
    "primaryReviewer",
    "specialistReviewers",
    "legalBasis",
    "requiredFactFields",
    "keywords",
}


class LegalKnowledgeError(ValueError):
    """Raised when the legal knowledge map is missing or malformed."""


def load_legal_knowledge_map(path: str | Path = DEFAULT_KNOWLEDGE_PATH) -> dict[str, Any]:
    knowledge_path = Path(path)
    if not knowledge_path.exists():
        raise LegalKnowledgeError(f"Legal knowledge map not found: {knowledge_path}")
    try:
        knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LegalKnowledgeError(f"Invalid legal knowledge map JSON: {knowledge_path}") from exc
    validate_legal_knowledge_map(knowledge)
    return knowledge


def validate_legal_knowledge_map(knowledge: dict[str, Any]) -> None:
    documents = knowledge.get("documents")
    if not isinstance(documents, dict) or not documents:
        raise LegalKnowledgeError("documents must be a non-empty object")

    firm_roles = load_firm_model(DEFAULT_FIRM_MODEL_PATH)["roles"]
    allowed_reviewers = set(firm_roles)

    for document_type, profile in documents.items():
        if not isinstance(profile, dict):
            raise LegalKnowledgeError(f"{document_type} profile must be an object")
        missing = sorted(REQUIRED_DOCUMENT_FIELDS - set(profile))
        if missing:
            raise LegalKnowledgeError(f"{document_type} missing fields: {', '.join(missing)}")
        reviewers = [profile["primaryReviewer"], *profile["specialistReviewers"]]
        unknown = sorted({reviewer for reviewer in reviewers if reviewer not in allowed_reviewers})
        if unknown:
            raise LegalKnowledgeError(f"{document_type} has unknown reviewers: {', '.join(unknown)}")
        for key in ["legalBasis", "requiredFactFields", "keywords"]:
            values = profile.get(key)
            if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
                raise LegalKnowledgeError(f"{document_type} {key} must be a non-empty string list")

    packages = knowledge.get("packages", {})
    if not isinstance(packages, dict):
        raise LegalKnowledgeError("packages must be an object")
    for package_id, package in packages.items():
        required_documents = package.get("requiredDocuments")
        if not isinstance(required_documents, list) or not required_documents:
            raise LegalKnowledgeError(f"{package_id} requiredDocuments must be a non-empty list")
        missing_documents = sorted(doc for doc in required_documents if doc not in documents)
        if missing_documents:
            raise LegalKnowledgeError(f"{package_id} references unknown documents: {', '.join(missing_documents)}")


def document_profile(document_type: str, knowledge: dict[str, Any] | None = None) -> dict[str, Any]:
    active = knowledge or load_legal_knowledge_map()
    try:
        return active["documents"][document_type]
    except KeyError as exc:
        raise LegalKnowledgeError(f"Unknown document type: {document_type}") from exc


def infer_required_documents(text: str, knowledge: dict[str, Any] | None = None) -> list[str]:
    active = knowledge or load_legal_knowledge_map()
    normalized = normalize(text)

    for package in active.get("packages", {}).values():
        package_keywords = [normalize(keyword) for keyword in package.get("keywords", [])]
        if package_keywords and sum(1 for keyword in package_keywords if keyword in normalized) >= 3:
            return list(package["requiredDocuments"])

    matches: list[str] = []
    for document_type, profile in active["documents"].items():
        keywords = [normalize(keyword) for keyword in profile["keywords"]]
        if any(keyword in normalized for keyword in keywords):
            matches.append(document_type)
    return matches


def required_reviewers_for_package(document_types: list[str], knowledge: dict[str, Any] | None = None) -> list[str]:
    active = knowledge or load_legal_knowledge_map()
    ordered: list[str] = []
    for role in ["documents"]:
        add_unique(ordered, role)
    for document_type in document_types:
        profile = document_profile(document_type, active)
        add_unique(ordered, profile["primaryReviewer"])
        for reviewer in profile["specialistReviewers"]:
            add_unique(ordered, reviewer)
    add_unique(ordered, "senior_review")
    return ordered


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def add_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)

