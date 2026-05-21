"""Firm operating model loader for Hermes We Law OS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MODEL_PATH = Path("config/firm-operating-model.json")
REQUIRED_TOP_LEVEL = {
    "firm",
    "allowedMatterStatuses",
    "allowedPackageStatuses",
    "allowedIssueStatuses",
    "missingInfoTaxonomy",
    "approvalTypes",
    "roles",
}
REQUIRED_MISSING_INFO = ["para_avanzar", "para_firma", "no_bloqueante"]
REQUIRED_ROLE_FIELDS = {
    "displayName",
    "paperclipCommentPrefix",
    "responsibilities",
    "allowedStatuses",
    "requiredArtifacts",
    "completionGates",
}


class FirmModelError(ValueError):
    """Raised when the firm operating model is missing or malformed."""


def load_firm_model(path: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
    model_path = Path(path)
    if not model_path.exists():
        raise FirmModelError(f"Firm operating model not found: {model_path}")
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FirmModelError(f"Invalid firm operating model JSON: {model_path}") from exc
    validate_firm_model(model)
    return model


def validate_firm_model(model: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - set(model))
    if missing:
        raise FirmModelError(f"Missing firm model sections: {', '.join(missing)}")

    firm = model.get("firm")
    if not isinstance(firm, dict) or firm.get("paperclipAdapterType") != "hermes_local":
        raise FirmModelError("firm.paperclipAdapterType must be hermes_local")
    _validate_controller(firm)

    roles = model.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise FirmModelError("roles must be a non-empty object")

    taxonomy = model.get("missingInfoTaxonomy")
    if taxonomy != REQUIRED_MISSING_INFO:
        raise FirmModelError("missingInfoTaxonomy must be para_avanzar, para_firma, no_bloqueante")

    allowed_issue_statuses = _non_empty_string_set(model, "allowedIssueStatuses")
    _validate_role_contracts(roles, allowed_issue_statuses)


def validate_workers(model: dict[str, Any], workers_by_role: dict[str, dict[str, Any]]) -> None:
    roles = model.get("roles", {})
    missing = sorted(role for role in workers_by_role if role not in roles)
    if missing:
        raise FirmModelError(f"Configured workers have missing firm role contracts: {', '.join(missing)}")


def role_contract(model: dict[str, Any], role: str) -> dict[str, Any]:
    roles = model.get("roles", {})
    if role not in roles:
        raise FirmModelError(f"Unknown firm role: {role}")
    return roles[role]


def paperclip_comment_prefix(model: dict[str, Any], role: str) -> str:
    return str(role_contract(model, role)["paperclipCommentPrefix"])


def required_artifact_names(model: dict[str, Any], role: str) -> list[str]:
    artifacts = role_contract(model, role)["requiredArtifacts"]
    return [str(artifact["name"]) for artifact in artifacts if artifact.get("required", True)]


def _validate_role_contracts(roles: dict[str, Any], allowed_issue_statuses: set[str]) -> None:
    prefixes: set[str] = set()
    for role, contract in roles.items():
        if not isinstance(contract, dict):
            raise FirmModelError(f"Role {role} must be an object")

        missing = sorted(REQUIRED_ROLE_FIELDS - set(contract))
        if missing:
            raise FirmModelError(f"Role {role} missing fields: {', '.join(missing)}")

        prefix = contract["paperclipCommentPrefix"]
        if not isinstance(prefix, str) or not prefix.endswith("WORK PRODUCT:"):
            raise FirmModelError(f"Role {role} must define a WORK PRODUCT comment prefix")
        if prefix in prefixes:
            raise FirmModelError(f"Duplicate Paperclip comment prefix: {prefix}")
        prefixes.add(prefix)

        _require_non_empty_strings(contract, "responsibilities", f"Role {role}")
        _require_non_empty_strings(contract, "completionGates", f"Role {role}")
        statuses = _require_non_empty_strings(contract, "allowedStatuses", f"Role {role}")
        unknown_statuses = sorted(statuses - allowed_issue_statuses)
        if unknown_statuses:
            raise FirmModelError(f"Role {role} has unknown statuses: {', '.join(unknown_statuses)}")

        artifacts = contract["requiredArtifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise FirmModelError(f"Role {role} must declare requiredArtifacts")
        artifact_names: set[str] = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise FirmModelError(f"Role {role} artifact must be an object")
            for key in ["name", "type", "required"]:
                if key not in artifact:
                    raise FirmModelError(f"Role {role} artifact missing {key}")
            if not isinstance(artifact["name"], str) or not artifact["name"]:
                raise FirmModelError(f"Role {role} artifact name must be a non-empty string")
            if artifact["name"] in artifact_names:
                raise FirmModelError(f"Role {role} has duplicate artifact {artifact['name']}")
            artifact_names.add(artifact["name"])
            if not isinstance(artifact["required"], bool):
                raise FirmModelError(f"Role {role} artifact required must be boolean")


def _validate_controller(firm: dict[str, Any]) -> None:
    controller = firm.get("controller")
    if not isinstance(controller, dict):
        raise FirmModelError("firm.controller must describe Hermes Director")
    if controller.get("displayName") != "Hermes Director":
        raise FirmModelError("firm.controller.displayName must be Hermes Director")
    if controller.get("paperclipWorker") is not False:
        raise FirmModelError("firm.controller.paperclipWorker must be false")
    _require_non_empty_strings(controller, "responsibilities", "Hermes Director")


def _non_empty_string_set(model: dict[str, Any], key: str) -> set[str]:
    values = model.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise FirmModelError(f"{key} must be a non-empty string list")
    return set(values)


def _require_non_empty_strings(contract: dict[str, Any], key: str, label: str) -> set[str]:
    values = contract.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise FirmModelError(f"{label} {key} must be a non-empty string list")
    return set(values)


load_firm_model.validate_workers = validate_workers  # type: ignore[attr-defined]
