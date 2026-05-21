"""Append-only matter event log for Hermes We Law OS."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any


DEFAULT_EVENT_ROOT = Path("data/matter_events")
EVENT_TYPES = {
    "intake",
    "source_added",
    "task_created",
    "document_created",
    "correction_requested",
    "qa_completed",
    "approval_requested",
    "approval_granted",
    "deadline_added",
    "payment_received",
}


class MatterEventError(ValueError):
    """Raised when a matter event is invalid."""


class MatterEventStore:
    """Store matter events as one JSON object per line."""

    def __init__(self, root: str | Path = DEFAULT_EVENT_ROOT):
        self.root = Path(root)

    def append(
        self,
        matter_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        actor: str = "Hermes",
        source: str = "local",
    ) -> dict[str, Any]:
        existing = self.read(matter_id)
        event = {
            "id": f"EVT-{len(existing) + 1:03d}",
            "matter_id": matter_id,
            "event_type": event_type,
            "timestamp": now(),
            "actor": actor,
            "source": source,
            "payload": payload,
        }
        validate_event(event)
        path = self.path_for(matter_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def read(self, matter_id: str) -> list[dict[str, Any]]:
        path = self.path_for(matter_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            validate_event(event)
            events.append(event)
        return events

    def path_for(self, matter_id: str) -> Path:
        return self.root / matter_id / "events.jsonl"


def replay_matter_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "matter_id": None,
        "client": {},
        "matter": {},
        "documents": [],
        "tasks": [],
        "sources": [],
        "corrections": [],
        "qa": [],
        "approvals": [],
        "deadlines": [],
        "payments": [],
        "recent_events": [],
    }

    for event in events:
        validate_event(event)
        state["matter_id"] = event["matter_id"]
        payload = event.get("payload", {})
        event_type = event["event_type"]
        state["recent_events"].append(f"{event_type}: {event.get('actor', 'Hermes')}")

        if event_type == "intake":
            state["client"].update(payload.get("client", {}))
            state["matter"].update(payload.get("matter", {}))
        elif event_type == "source_added":
            append_payload_item(state["sources"], payload, "source")
        elif event_type == "task_created":
            append_payload_item(state["tasks"], payload, "task")
        elif event_type == "document_created":
            append_payload_item(state["documents"], payload, "document")
        elif event_type == "correction_requested":
            append_payload_item(state["corrections"], payload, "correction")
        elif event_type == "qa_completed":
            append_payload_item(state["qa"], payload, "qa")
        elif event_type in {"approval_requested", "approval_granted"}:
            append_payload_item(state["approvals"], payload, "approval")
        elif event_type == "deadline_added":
            append_payload_item(state["deadlines"], payload, "deadline")
        elif event_type == "payment_received":
            append_payload_item(state["payments"], payload, "payment")

    if state["matter_id"] and not state["matter"].get("id"):
        state["matter"]["id"] = state["matter_id"]
    return state


def validate_event(event: dict[str, Any]) -> None:
    for key in ["id", "matter_id", "event_type", "timestamp", "actor", "payload"]:
        if key not in event:
            raise MatterEventError(f"matter event missing {key}")
    if event["event_type"] not in EVENT_TYPES:
        raise MatterEventError(f"unknown matter event type: {event['event_type']}")
    if not isinstance(event["payload"], dict):
        raise MatterEventError("matter event payload must be an object")


def append_payload_item(target: list[dict[str, Any]], payload: dict[str, Any], key: str) -> None:
    item = payload.get(key, payload)
    if isinstance(item, dict):
        target.append(dict(item))


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
