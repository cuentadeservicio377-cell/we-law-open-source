#!/usr/bin/env python3
"""Offline smoke for the Hermes We Law firm command spine."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "hermes-welaw-core" / "tools"))

from field_intake_bridge import BridgePaths, build_field_intake


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        paths = BridgePaths(
            clients=base / "clients.json",
            matters=base / "matters.json",
            documents=base / "documents.json",
            tasks=base / "tasks.json",
            inbox=base / "inbox",
            generated=base / "generated",
            memory_root=base / "memory",
            intake_sessions=base / "intake_sessions.json",
            matter_events=base / "matter_events",
            manifest=base / "manifest.json",
        )
        for path in [paths.clients, paths.matters, paths.documents, paths.tasks]:
            path.write_text("[]", encoding="utf-8")
        paths.manifest.write_text(
            json.dumps(
                {
                    "companyId": "company-1",
                    "apiUrl": "http://127.0.0.1:3100/api",
                    "agents": {
                        "master": "agent-master",
                        "intake": "agent-intake",
                        "documents": "agent-docs",
                        "deadlines": "agent-deadlines",
                    },
                }
            ),
            encoding="utf-8",
        )
        result = build_field_intake(
            "Fui a ver a Clinica Demo. Quiere terminos, privacidad, NDA y contrato de desarrollo.",
            paths=paths,
            apply_local=True,
        )

    roles = [assignment["role"] for assignment in result["delegation_plan"]["assignments"]]
    issue_roles = [issue["role"] for issue in result["paperclip_issue_requests"]]
    errors: list[str] = []
    for required in ["command_record", "matter_brief", "delegation_plan", "workspace_manifest", "approval_gates", "partner_briefing"]:
        if required not in result:
            errors.append(f"missing {required}")
    for required_role in ["master", "intake", "file", "sheets", "legal_research", "documents", "deadlines", "editorial", "senior_review"]:
        if required_role not in roles:
            errors.append(f"delegation missing role {required_role}")
    for issue in result["paperclip_issue_requests"]:
        if "context_package" not in issue:
            errors.append(f"issue {issue['title']} missing context package")
    output = {
        "ok": not errors,
        "command_id": result["command_record"]["id"],
        "matter_id": result["matter"]["id"],
        "delegation_roles": roles,
        "paperclip_issue_roles": issue_roles,
        "workspace_write_gate": result["workspace_manifest"]["write_gate"]["mode"],
        "errors": errors,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
