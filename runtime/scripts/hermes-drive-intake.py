#!/usr/bin/env python3
"""Run Hermes We Law intake from a live Google Drive folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "skills/hermes-welaw-intake/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from drive_intake_orchestrator import run_live_drive_intake
from drive_intake_orchestrator import check_paperclip_staff_ready


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drive-folder-url", required=True)
    parser.add_argument("--partner-context", default="")
    parser.add_argument("--partner-context-file")
    parser.add_argument("--apply-local", action="store_true")
    parser.add_argument("--apply-workspace", action="store_true", help="Write control-master rows and packet JSON to Google Workspace.")
    parser.add_argument("--apply-paperclip", action="store_true")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--skip-paperclip-ready-check", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    partner_context = args.partner_context
    if args.partner_context_file:
        partner_context = Path(args.partner_context_file).read_text(encoding="utf-8")

    if args.apply_paperclip and not args.skip_paperclip_ready_check:
        readiness = check_paperclip_staff_ready(api_url=args.api_url)
        if not readiness["ok"]:
            print(json.dumps(readiness, ensure_ascii=False, indent=2))
            return 2

    result = run_live_drive_intake(
        drive_folder_url=args.drive_folder_url,
        partner_context=partner_context,
        apply_local=args.apply_local,
        apply_workspace=args.apply_workspace,
        apply_paperclip=args.apply_paperclip,
        api_url=args.api_url,
    )
    if args.compact:
        print(json.dumps(compact_summary(result), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def compact_summary(result: dict[str, object]) -> dict[str, object]:
    packet = result["packet"]
    assert isinstance(packet, dict)
    artifacts = packet["artifacts"]
    assert isinstance(artifacts, dict)
    snapshot = artifacts.get("dashboard_snapshot", {})
    assert isinstance(snapshot, dict)
    return {
        "ok": result["ok"],
        "mode": packet.get("mode"),
        "workspace_read": packet.get("workspace", {}).get("read") if isinstance(packet.get("workspace"), dict) else None,
        "client": snapshot.get("client_name"),
        "matter": snapshot.get("matter_description"),
        "required_documents": snapshot.get("required_documents", []),
        "missing_count": snapshot.get("missing_count"),
        "persisted_packet": result.get("persisted_packet"),
        "workspace_writeback": result.get("workspace_writeback"),
        "document_writeback": packet.get("workspace", {}).get("document_writeback")
        if isinstance(packet.get("workspace"), dict)
        else None,
        "paperclip_created": [
            {
                "role": item.get("role"),
                "identifier": (item.get("issue") or {}).get("identifier"),
                "id": (item.get("issue") or {}).get("id"),
            }
            for item in result.get("paperclip_created", [])
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
