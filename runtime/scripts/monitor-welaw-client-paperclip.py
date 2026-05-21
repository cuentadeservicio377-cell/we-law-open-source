#!/usr/bin/env python3
"""Monitor a We Law Paperclip client run and fail on missing legal output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import request


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "runtime/config/paperclip-welaw-instance.json"
FIRM_MODEL_PATH = ROOT / "config/firm-operating-model.json"
DEFAULT_FORBIDDEN_ROOT = "${HERMES_WELAW_FORBIDDEN_ROOT:-/path/to/noncanonical-backup}"
BAD_RUN_STATUSES = {"error", "failed", "timed_out", "timeout"}
EDITORIAL_REQUIRED_MARKERS = {
    "EDITORIAL_SPEC",
    "RENDER_MANIFEST",
    "VISUAL_QA",
    "CLIENT_DELIVERY_LINKS",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identifiers", nargs="*", default=[])
    parser.add_argument("--range", dest="identifier_range", default="")
    parser.add_argument("--company-id", default="")
    parser.add_argument("--api-url", default="")
    parser.add_argument("--wait-sec", type=int, default=0)
    parser.add_argument("--poll-sec", type=int, default=15)
    parser.add_argument("--forbidden-root", default=DEFAULT_FORBIDDEN_ROOT)
    parser.add_argument("--fail-on-unfinished", action="store_true")
    parser.add_argument("--fail-on-empty-comments", action="store_true")
    parser.add_argument("--fail-on-forbidden-root", action="store_true")
    parser.add_argument("--fail-on-bad-run-status", action="store_true")
    parser.add_argument("--fail-on-missing-editorial", action="store_true")
    parser.add_argument("--fail-on-missing-cross-review", action="store_true")
    parser.add_argument("--fail-on-missing-prefixes", action="store_true")
    parser.add_argument("--fail-on-stale-manifests", action="store_true")
    args = parser.parse_args()

    manifest = load_json(MANIFEST_PATH, {})
    api_url = (args.api_url or manifest.get("apiUrl") or "http://127.0.0.1:3100/api").rstrip("/")
    company_id = args.company_id or manifest.get("companyId")
    if not company_id:
        raise SystemExit("Missing company id")

    identifiers = set(args.identifiers)
    if args.identifier_range:
        identifiers.update(expand_identifier_range(args.identifier_range))
    if not identifiers:
        raise SystemExit("Provide --identifiers or --range")

    deadline = time.time() + max(args.wait_sec, 0)
    while True:
        report = build_report(api_url, company_id, identifiers, args.forbidden_root)
        unfinished = [
            item
            for item in report["issues"]
            if item.get("missing") or item.get("status") not in {"done", "cancelled"}
        ]
        if not unfinished or time.time() >= deadline:
            break
        time.sleep(max(args.poll_sec, 1))

    report = build_report(api_url, company_id, identifiers, args.forbidden_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    failures = evaluate_failures(
        report,
        fail_on_unfinished=args.fail_on_unfinished,
        fail_on_empty_comments=args.fail_on_empty_comments,
        fail_on_forbidden_root=args.fail_on_forbidden_root,
        fail_on_bad_run_status=args.fail_on_bad_run_status,
        fail_on_missing_editorial=args.fail_on_missing_editorial,
        fail_on_missing_cross_review=args.fail_on_missing_cross_review,
        fail_on_missing_prefixes=args.fail_on_missing_prefixes,
        fail_on_stale_manifests=args.fail_on_stale_manifests,
    )
    if failures:
        print("MONITOR FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 2
    return 0


def expand_identifier_range(value: str) -> list[str]:
    if "-" not in value:
        return [value]
    prefix, start_text, end_text = value.split("-", 2)
    start = int(start_text)
    end = int(end_text)
    return [f"{prefix}-{number}" for number in range(start, end + 1)]


def build_report(api_url: str, company_id: str, identifiers: set[str], forbidden_root: str) -> dict[str, Any]:
    all_issues = get_json(f"{api_url}/companies/{company_id}/issues?limit=200")
    if isinstance(all_issues, dict):
        all_issues = all_issues.get("issues", [])
    by_identifier = {issue.get("identifier"): issue for issue in all_issues if isinstance(issue, dict)}
    agents = get_json(f"{api_url}/companies/{company_id}/agents")
    if isinstance(agents, dict):
        agents = agents.get("agents", [])
    agent_status = {
        agent.get("id"): {
            "name": agent.get("name"),
            "status": agent.get("status"),
            "adapterType": agent.get("adapterType"),
            "role": (agent.get("metadata") or {}).get("welawRole") if isinstance(agent.get("metadata"), dict) else None,
        }
        for agent in agents
        if isinstance(agent, dict)
    }

    issues = []
    for identifier in sorted(identifiers, key=identifier_sort_key):
        issue = by_identifier.get(identifier)
        if not issue:
            issues.append({"identifier": identifier, "missing": True})
            continue
        issue_id = issue["id"]
        comments = get_json(f"{api_url}/issues/{issue_id}/comments")
        if isinstance(comments, dict):
            comments = comments.get("comments", [])
        runs = get_json(f"{api_url}/issues/{issue_id}/runs")
        if isinstance(runs, dict):
            runs = runs.get("runs", [])
        comment_text = "\n".join(str(comment.get("body") or comment.get("content") or "") for comment in comments if isinstance(comment, dict))
        description = strip_runtime_context(str(issue.get("description") or ""))
        last_run = runs[-1] if runs else {}
        agent_id = issue.get("assigneeAgentId")
        issues.append(
            {
                "identifier": identifier,
                "id": issue_id,
                "title": issue.get("title"),
                "status": issue.get("status") or issue.get("state"),
                "role": extract_role(description) or (agent_status.get(agent_id) or {}).get("role") or "",
                "assigneeAgentId": agent_id,
                "assignee": agent_status.get(agent_id),
                "comment_count": len(comments),
                "run_count": len(runs),
                "last_run_status": last_run.get("status") if isinstance(last_run, dict) else None,
                "last_run_reason": (last_run.get("resultJson") or {}).get("stopReason") if isinstance(last_run, dict) else None,
                "forbidden_root_seen": forbidden_root in description or forbidden_root in comment_text,
                "has_runtime_context": "HERMES WE LAW RUNTIME CONTEXT" in description,
                "comment_text": comment_text,
                "last_comment_preview": preview_comment(comments[-1]) if comments else "",
            }
        )

    return {
        "ok": True,
        "canonical_root": str(ROOT),
        "forbidden_root": forbidden_root,
        "company_id": company_id,
        "issue_count": len(issues),
        "issues": issues,
        "agent_status_counts": count_agent_status(agent_status.values()),
    }


def evaluate_failures(
    report: dict[str, Any],
    *,
    fail_on_unfinished: bool = False,
    fail_on_empty_comments: bool = False,
    fail_on_forbidden_root: bool = False,
    fail_on_bad_run_status: bool = False,
    fail_on_missing_editorial: bool = False,
    fail_on_missing_cross_review: bool = False,
    fail_on_missing_prefixes: bool = False,
    fail_on_stale_manifests: bool = False,
    required_prefixes: dict[str, str] | None = None,
) -> list[str]:
    failures: list[str] = []
    issues = [item for item in report.get("issues", []) if isinstance(item, dict)]
    searchable_text = "\n".join(issue_comment_text(item) for item in issues)

    for item in issues:
        identifier = str(item.get("identifier") or "unknown")
        if item.get("missing"):
            failures.append(f"{identifier} missing issue")
            continue
        status = str(item.get("status") or "unknown")
        comment_count = int(item.get("comment_count") or 0)
        last_run_status = str(item.get("last_run_status") or "").lower()
        comment_text = issue_comment_text(item)

        if fail_on_unfinished and status not in {"done", "cancelled"}:
            failures.append(f"{identifier} status={status}")
        if fail_on_empty_comments and comment_count == 0:
            failures.append(f"{identifier} has no comments")
        if fail_on_forbidden_root and item.get("forbidden_root_seen"):
            failures.append(f"{identifier} references forbidden root")
        if fail_on_bad_run_status and last_run_status in BAD_RUN_STATUSES:
            failures.append(f"{identifier} last_run_status={last_run_status}")
        if fail_on_missing_prefixes:
            prefix = (required_prefixes or required_prefixes_from_firm_model(issues)).get(identifier)
            if prefix and prefix not in comment_text:
                failures.append(f"{identifier} missing required prefix {prefix}")
        if fail_on_stale_manifests:
            failures.extend(evaluate_manifest_failures(item))

    if fail_on_missing_cross_review and "PACKAGE_CROSS_REVIEW" not in searchable_text:
        failures.append("missing PACKAGE_CROSS_REVIEW")

    if fail_on_missing_editorial and not has_editorial_package(issues):
        failures.append("missing complete editorial package")
    return failures


def has_editorial_package(issues: list[dict[str, Any]]) -> bool:
    for item in issues:
        text = issue_comment_text(item)
        if "EDITORIAL WORK PRODUCT:" not in text:
            continue
        if all(marker in text for marker in EDITORIAL_REQUIRED_MARKERS):
            return True
    return False


def issue_comment_text(issue: dict[str, Any]) -> str:
    return "\n".join(
        value
        for value in (
            str(issue.get("comment_text") or ""),
            str(issue.get("last_comment_preview") or ""),
        )
        if value
    )


def required_prefixes_from_firm_model(issues: list[dict[str, Any]]) -> dict[str, str]:
    roles = load_json(FIRM_MODEL_PATH, {}).get("roles", {})
    role_prefixes = {
        role: config.get("paperclipCommentPrefix")
        for role, config in roles.items()
        if isinstance(config, dict) and isinstance(config.get("paperclipCommentPrefix"), str)
    }
    return {
        str(issue.get("identifier")): role_prefixes[str(issue.get("role"))]
        for issue in issues
        if str(issue.get("role")) in role_prefixes and issue.get("identifier")
    }


def evaluate_manifest_failures(issue: dict[str, Any]) -> list[str]:
    identifier = str(issue.get("identifier") or "unknown")
    failures: list[str] = []
    for manifest_path in manifest_paths_from_comment(issue_comment_text(issue)):
        if not manifest_path.exists():
            failures.append(f"{identifier} manifest missing on disk {manifest_path}")
            continue
        manifest = load_json(manifest_path, {})
        artifact_paths = manifest_artifact_paths(manifest)
        historical_paths = set(manifest_item_paths(manifest.get("historical_sources", [])))
        missing_paths = [path for path in artifact_paths if not path.exists()]
        stale_active_paths = [
            path
            for path in artifact_paths
            if path.exists() and path not in historical_paths and has_old_wel_segment(path, identifier)
        ]
        if missing_paths:
            failures.append(f"{identifier} manifest_paths_must_exist {manifest_path}")
        if stale_active_paths:
            failures.append(f"{identifier} old WEL output is active {manifest_path}")
    return failures


def manifest_paths_from_comment(comment_text: str) -> list[Path]:
    paths: list[Path] = []
    for match in re.findall(r"(?:(?:/|workspace/)[^\s'\"`]*DELIVERABLE_MANIFEST\.json)", comment_text):
        path = Path(match)
        if str(path).startswith("/workspace/"):
            path = Path(str(path).lstrip("/"))
        paths.append(path if path.is_absolute() else ROOT / path)
    return list(dict.fromkeys(path.resolve() for path in paths))


def manifest_artifact_paths(manifest: dict[str, Any]) -> list[Path]:
    return manifest_item_paths(manifest.get("artifacts", [])) + manifest_item_paths(manifest.get("artifacts_produced", []))


def manifest_item_paths(items: Any) -> list[Path]:
    paths: list[Path] = []
    if not isinstance(items, list):
        return paths
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get("path")
        if isinstance(value, str) and value:
            path = Path(value)
            paths.append((path if path.is_absolute() else ROOT / path).resolve())
    return paths


def has_old_wel_segment(path: Path, current_identifier: str) -> bool:
    current = current_identifier.upper()
    return any(re.fullmatch(r"WEL-\d+.*", segment.upper()) and current not in segment.upper() for segment in path.parts)


def extract_role(description: str) -> str:
    match = re.search(r"^Rol:\s*([a-z0-9_/-]+)\s*$", description, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip().lower() if match else ""


def count_agent_status(agents: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for agent in agents:
        status = str(agent.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def preview_comment(comment: dict[str, Any]) -> str:
    body = str(comment.get("body") or comment.get("content") or "")
    return " ".join(body.split())[:600]


def strip_runtime_context(description: str) -> str:
    marker = "HERMES WE LAW RUNTIME CONTEXT"
    if marker not in description:
        return description
    return description.split(marker, 1)[0]


def identifier_sort_key(identifier: str) -> tuple[str, int]:
    if "-" not in identifier:
        return (identifier, 0)
    prefix, number = identifier.rsplit("-", 1)
    try:
        return (prefix, int(number))
    except ValueError:
        return (identifier, 0)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(url: str) -> Any:
    with request.urlopen(url, timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None


if __name__ == "__main__":
    raise SystemExit(main())
