"""Firm command spine contract for Hermes We Law OS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SPINE_PATH = Path("config/firm-command-spine.json")
REQUIRED_ACTORS = {
    "pablo": "owner",
    "hermes": "managing_partner",
    "paperclip_staff": "legal_staff",
    "workspace": "office_system",
    "dashboard": "control_desk",
}
REQUIRED_ARTIFACTS = {
    "command_record",
    "matter_brief",
    "delegation_plan",
    "workspace_manifest",
    "worker_context_packages",
    "approval_gates",
    "partner_briefing",
}
REQUIRED_STAGE_IDS = {
    "receive_instruction",
    "resolve_context",
    "open_command_record",
    "delegate_staff_work",
    "execute_staff_work",
    "maintain_workspace",
    "review_and_approve",
    "brief_partner",
}


class FirmCommandSpineError(ValueError):
    """Raised when the firm command spine is missing or malformed."""


def load_firm_command_spine(path: str | Path = DEFAULT_SPINE_PATH) -> dict[str, Any]:
    spine_path = Path(path)
    if not spine_path.exists():
        raise FirmCommandSpineError(f"Firm command spine not found: {spine_path}")
    try:
        spine = json.loads(spine_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FirmCommandSpineError(f"Invalid firm command spine JSON: {spine_path}") from exc
    validate_firm_command_spine(spine)
    return spine


def validate_firm_command_spine(spine: dict[str, Any]) -> None:
    if spine.get("kind") != "firm_command_spine":
        raise FirmCommandSpineError("kind must be firm_command_spine")
    if spine.get("schemaVersion") != "1":
        raise FirmCommandSpineError("schemaVersion must be 1")
    if spine.get("firm") != "We Law S.C.":
        raise FirmCommandSpineError("firm must be We Law S.C.")

    actors = spine.get("actors")
    if not isinstance(actors, dict):
        raise FirmCommandSpineError("actors must be an object")
    missing_actors = sorted(set(REQUIRED_ACTORS) - set(actors))
    if missing_actors:
        raise FirmCommandSpineError(f"Missing command spine actors: {', '.join(missing_actors)}")
    for actor_id, authority in REQUIRED_ACTORS.items():
        actor = actors.get(actor_id)
        if not isinstance(actor, dict):
            raise FirmCommandSpineError(f"Actor {actor_id} must be an object")
        if actor.get("authority") != authority:
            raise FirmCommandSpineError(f"Actor {actor_id} authority must be {authority}")
        _require_non_empty_strings(actor, "responsibilities", f"Actor {actor_id}")

    chain = spine.get("chainOfCommand")
    if chain != list(REQUIRED_ACTORS):
        raise FirmCommandSpineError("chainOfCommand must be pablo, hermes, paperclip_staff, workspace, dashboard")

    stages = spine.get("lifecycleStages")
    if not isinstance(stages, list) or not stages:
        raise FirmCommandSpineError("lifecycleStages must be a non-empty list")
    stage_ids = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise FirmCommandSpineError("Each lifecycle stage must be an object")
        for key in ["id", "owner", "description"]:
            if not isinstance(stage.get(key), str) or not stage[key]:
                raise FirmCommandSpineError(f"Lifecycle stage missing {key}")
        if stage["owner"] not in actors:
            raise FirmCommandSpineError(f"Lifecycle stage owner is not an actor: {stage['owner']}")
        stage_ids.add(stage["id"])
    missing_stages = sorted(REQUIRED_STAGE_IDS - stage_ids)
    if missing_stages:
        raise FirmCommandSpineError(f"Missing command spine stages: {', '.join(missing_stages)}")

    artifacts = spine.get("requiredArtifacts")
    if not isinstance(artifacts, list):
        raise FirmCommandSpineError("requiredArtifacts must be a list")
    missing_artifacts = sorted(REQUIRED_ARTIFACTS - set(artifacts))
    if missing_artifacts:
        raise FirmCommandSpineError(f"Missing command spine artifacts: {', '.join(missing_artifacts)}")

    _require_non_empty_strings(spine, "approvalGateTypes", "Firm command spine")
    _require_non_empty_strings(spine, "dashboardPrinciples", "Firm command spine")


def command_spine_summary(spine: dict[str, Any] | None = None) -> dict[str, Any]:
    active_spine = spine or load_firm_command_spine()
    return {
        "kind": active_spine["kind"],
        "firm": active_spine["firm"],
        "chainOfCommand": active_spine["chainOfCommand"],
        "requiredArtifacts": active_spine["requiredArtifacts"],
        "dashboardPrinciples": active_spine["dashboardPrinciples"],
    }


def _require_non_empty_strings(container: dict[str, Any], key: str, label: str) -> set[str]:
    values = container.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise FirmCommandSpineError(f"{label} {key} must be a non-empty string list")
    return set(values)


load_firm_command_spine.validate = validate_firm_command_spine  # type: ignore[attr-defined]
