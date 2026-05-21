"""Load and validate the We Law legal worker operating contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONTRACT_PATH = Path("config/legal-worker-operating-contract.json")


class LegalWorkerContractError(ValueError):
    """Raised when the legal worker contract is missing or incomplete."""


REQUIRED_ROLE_KEYS = {
    "master",
    "intake",
    "file",
    "sheets",
    "legal_research",
    "documents",
    "privacy",
    "ip_software",
    "litigation",
    "deadlines",
    "collections",
    "editorial",
    "senior_review",
    "admin",
    "despacho_legal",
    "recepcionista_juridico",
    "documentos_legales",
    "asuntos_juridicos",
    "cobranza",
    "admin_biblioteca",
}

REQUIRED_CLAUSE_IDS = {
    "google_docs_live_update",
    "update_not_duplicate",
    "cross_document_review",
    "package_approval_payload",
    "weasyprint_a4_reference",
}

REQUIRED_DOCUMENT_STATES = {
    "borrador_inicial",
    "borrador_operativo",
    "borrador_casi_firmable",
    "listo_revision_cliente",
    "listo_firma",
    "no_aplica",
}


def load_legal_worker_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Return the validated legal worker operating contract."""

    contract_path = Path(path)
    if not contract_path.exists():
        raise LegalWorkerContractError(f"Contract file not found: {contract_path}")
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    validate_legal_worker_contract(data)
    return data


def validate_legal_worker_contract(data: dict[str, Any]) -> None:
    """Validate the clauses that keep legal workers from becoming shallow agents."""

    if data.get("schemaVersion") != "1":
        raise LegalWorkerContractError("Contract schemaVersion must be 1")

    roles = set(data.get("roleContracts", {}))
    missing_roles = sorted(REQUIRED_ROLE_KEYS - roles)
    if missing_roles:
        raise LegalWorkerContractError(f"Missing role contracts: {', '.join(missing_roles)}")
    incomplete_roles = []
    for role_key in sorted(REQUIRED_ROLE_KEYS):
        role = data.get("roleContracts", {}).get(role_key, {})
        if role_key in {"despacho_legal", "recepcionista_juridico", "documentos_legales", "asuntos_juridicos", "cobranza", "admin_biblioteca"}:
            continue
        for field in ["paperclipCommentPrefix", "requiredArtifacts", "blockers", "closureSemantics"]:
            if not role.get(field):
                incomplete_roles.append(f"{role_key}.{field}")
    if incomplete_roles:
        raise LegalWorkerContractError(f"Incomplete role contracts: {', '.join(incomplete_roles)}")

    states = set(data.get("matterState", {}).get("documentStates", []))
    missing_states = sorted(REQUIRED_DOCUMENT_STATES - states)
    if missing_states:
        raise LegalWorkerContractError(
            f"Missing document states: {', '.join(missing_states)}"
        )

    clause_ids = _collect_clause_ids(data)
    missing_clauses = sorted(REQUIRED_CLAUSE_IDS - clause_ids)
    if missing_clauses:
        raise LegalWorkerContractError(
            f"Missing required clauses: {', '.join(missing_clauses)}"
        )

    forbidden = ["drive.google.com", "oauth", "telegram_token", "client_secret"]
    serialized = json.dumps(data, ensure_ascii=True).lower()
    leaked = [term for term in forbidden if term in serialized]
    if leaked:
        raise LegalWorkerContractError(f"Contract contains forbidden runtime data: {leaked}")


def _collect_clause_ids(value: Any) -> set[str]:
    clause_ids: set[str] = set()
    if isinstance(value, dict):
        clause_id = value.get("clauseId")
        if isinstance(clause_id, str):
            clause_ids.add(clause_id)
        for child in value.values():
            clause_ids.update(_collect_clause_ids(child))
    elif isinstance(value, list):
        for child in value:
            clause_ids.update(_collect_clause_ids(child))
    return clause_ids
