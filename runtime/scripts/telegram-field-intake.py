#!/usr/bin/env python3
"""CLI entrypoint for Telegram-style We Law field intake."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "skills/hermes-welaw-core/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from field_intake_bridge import apply_paperclip_issues, build_field_intake


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="*", help="Telegram-style field message.")
    parser.add_argument("--message-file", help="Read the field message from a text file.")
    parser.add_argument("--source", default="telegram")
    parser.add_argument("--apply-local", action="store_true", help="Persist local client/matter/memory/context files.")
    parser.add_argument("--apply-paperclip", action="store_true", help="Create real Paperclip issues.")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--compact", action="store_true", help="Print compact summary only.")
    args = parser.parse_args()

    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
    else:
        message = " ".join(args.message).strip()
    if not message:
        parser.error("message or --message-file is required")

    result = build_field_intake(message, source=args.source, apply_local=args.apply_local)
    if args.apply_paperclip:
        result["paperclip_created_issues"] = apply_paperclip_issues(result, args.api_url)

    if args.compact:
        print(json.dumps(compact_summary(result), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def compact_summary(result: dict[str, object]) -> dict[str, object]:
    client = result["client"]
    matter = result["matter"]
    assert isinstance(client, dict)
    assert isinstance(matter, dict)
    return {
        "ok": True,
        "client": {"id": client.get("id"), "nombre": client.get("nombre")},
        "matter": {"id": matter.get("id"), "tipo": matter.get("tipo"), "fase": matter.get("fase")},
        "planned_documents": [item["title"] for item in result.get("planned_documents", [])],
        "planned_tasks": [item["title"] for item in result.get("planned_tasks", [])],
        "paperclip_created": [
            {
                "role": item.get("role"),
                "identifier": (item.get("issue") or {}).get("identifier"),
                "id": (item.get("issue") or {}).get("id"),
            }
            for item in result.get("paperclip_created_issues", [])
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
