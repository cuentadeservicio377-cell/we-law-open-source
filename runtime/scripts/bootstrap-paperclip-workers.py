#!/usr/bin/env python3
"""Bootstrap Paperclip Hermes workers for We Law."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/paperclip-hermes-agents.json"
FIRM_MODEL_PATH = ROOT / "config/firm-operating-model.json"
LEGAL_WORKER_CONTRACT_PATH = ROOT / "config/legal-worker-operating-contract.json"
DEFAULT_HERMES_COMMAND = "${HERMES_COMMAND:-hermes}"
DEFAULT_RUNTIME_PATH = "${HOMEBREW_BIN:-/usr/local/bin}:/Users/local-user/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

sys.path.insert(0, str(ROOT / "skills" / "hermes-welaw-core" / "tools"))
from firm_model import load_firm_model, paperclip_comment_prefix, required_artifact_names, role_contract, validate_workers
from legal_worker_contract import load_legal_worker_contract


def build_role_contract(worker: dict[str, Any], firm_model: dict[str, Any] | None = None) -> str:
    role = str(worker["role"])
    model = firm_model or load_firm_model(FIRM_MODEL_PATH)
    contract = role_contract(model, role)
    prefix = paperclip_comment_prefix(model, role)
    artifacts = required_artifact_names(model, role)
    artifact_lines = "\n".join(f"- {artifact}" for artifact in artifacts)
    gate_lines = "\n".join(f"- {gate}" for gate in contract["completionGates"])
    responsibilities = "\n".join(f"- {item}" for item in contract["responsibilities"])
    legal_contract = load_legal_worker_contract(LEGAL_WORKER_CONTRACT_PATH)
    deterministic_tools = legal_contract.get("roleContracts", {}).get(role, {}).get("deterministicTools", [])
    deterministic_tool_lines = "\n".join(f"- {tool}" for tool in deterministic_tools) or "- None declared for this role."

    if role == "documents":
        return f"""Documentos Legales production contract:
You are acting as a We Law lawyer, not as a formatting worker.
Mandatory source of truth: LEGAL WORKER OPERATING CONTRACT at config/legal-worker-operating-contract.json.
Paperclip writeback prefix: {prefix}
Responsibilities:
{responsibilities}
Required artifacts from firm operating model:
{artifact_lines}

Deterministic helper/validator tools for this role:
{deterministic_tool_lines}

For every real legal-document issue, produce a traceable legal work product before closing:
1. Source audit: read the issue body, existing comments, referenced local folders, Google Drive/Docs links when credentials are available, original DOCX/PDF/text files, meeting notes/transcripts, correction files, existing drafts, templates, and editorial references.
2. Evidence extraction: create EVIDENCE_MAP.md with source file or link, relevant fact, confidence, and affected document. Do not dump sensitive data into Paperclip comments; keep detailed evidence in the workspace.
3. Data ledger: create DATA_LEDGER.json with parties, platform facts, commercial terms, privacy facts, technical facts, signature/fiscal data, missing fields, source, and confidence.
4. Corrections: create CORRECTIONS_APPLIED.md mapping each requested correction to applied location, pending blocker, or explicit rejection reason.
5. Drafting: follow the google_docs_live_update and update_not_duplicate clauses. Read existing live Google Docs with gws docs documents get when available, and update them with gws docs documents batchUpdate instead of creating duplicates unless a new version is explicitly required.
6. Cross-document review: for packages, follow cross_document_review. Load all related documents together and verify parties, dates, amounts, definitions, IP ownership, privacy roles, software descriptions, payment mechanics, termination, confidentiality and signature data before approval.
7. Editorial output: if Kami/Canva/editorial output is requested, use the available Kami skill or local editorial renderer, state whether the result preserves Canva design or is a Kami-style reconstruction, and create HTML/PDF or the best available format. When a reference package exists, prefer WeasyPrint A4 and require editorial reference QA; do not ship compressed Chrome/Letter output as final client deliverable.
8. QA: create PLACEHOLDER_REPORT.md, DELIVERABLE_MANIFEST.json, and LEGAL_QA.md. LEGAL_QA.md must state package_status as draft, review, client-deliverable, blocked, or signature-ready.
9. Fresh output: follow fresh_issue_output. Create a fresh current_issue_output directory for this issue. Old WEL output may be evidence, not final artifact; put old WEL paths only under historical_sources. DELIVERABLE_MANIFEST.json must pass manifest_paths_must_exist and must include at least one fresh current issue artifact.
10. Paperclip writeback: post a comment prefixed LEGAL WORK PRODUCT: with local paths, Drive links if uploaded, package_status, blockers, placeholder count, and exact QA files.

Completion gates:
- Firm model gates:
{gate_lines}
- Do not use HERMES LIVE OK for real legal-document work.
- Do not close real work from shallow artifacts, reduced summaries, or markdown-only output when Google Docs/editorial delivery was requested.
- Do not mark client-deliverable until google_docs_live_update, update_not_duplicate, cross_document_review when package work exists, and WeasyPrint A4 editorial QA when requested have passed or are honestly blocked.
- Do not mark the issue done unless EVIDENCE_MAP.md, DATA_LEDGER.json, CORRECTIONS_APPLIED.md, PLACEHOLDER_REPORT.md, DELIVERABLE_MANIFEST.json, and LEGAL_QA.md exist, or unless LEGAL_QA.md declares a hard blocker caused by inaccessible required sources.
- Do not mark a package signature-ready when placeholders, unresolved corrections, or missing client data remain.
- If the issue asks for final/signature-ready documents and blockers remain, post LEGAL BLOCKER: and leave the issue not done."""

    return f"""Production contract:
Execute the assigned legal-operations work using the firm operating model, create durable workspace evidence when files are changed, write a concise Paperclip comment with the role-specific prefix, and mark the issue done only after the requested work or an explicit blocker report is posted.

Mandatory source of truth: LEGAL WORKER OPERATING CONTRACT at config/legal-worker-operating-contract.json.
Paperclip writeback prefix: {prefix}

Responsibilities:
{responsibilities}

Required artifacts:
{artifact_lines}

Deterministic helper/validator tools for this role:
{deterministic_tool_lines}

Completion gates:
{gate_lines}"""


def build_live_prompt_template(worker: dict[str, Any], firm_model: dict[str, Any] | None = None) -> str:
    role_prompt = str(worker["promptTemplate"]).strip()
    skills = ", ".join(worker.get("skills", []))
    role_contract = build_role_contract(worker, firm_model).strip()
    return f"""Paperclip API safety rule:
Never prepare, export, print, derive or inspect Paperclip credentials yourself.
Never call curl directly for Paperclip writes.
Never use a board, browser, or local-board session for Paperclip API writes.
Use only the checked-in helper scripts listed below; they load local trusted credentials and runtime IDs safely.

You are "{{{{agentName}}}}" inside We Law S.C.'s Hermes Business OS.
Role contract: {role_prompt}
Role key: {worker["role"]}
Enabled We Law skills: {skills}

{role_contract}

Runtime identity:
- Agent ID: {{{{agentId}}}}
- Company ID: {{{{companyId}}}}
- Run ID: {{{{runId}}}}
- Paperclip API: {{{{paperclipApiUrl}}}}
- Canonical production root: {ROOT}
- Forbidden root: ${HERMES_WELAW_FORBIDDEN_ROOT:-/path/to/noncanonical-backup}
- Runtime cwd must resolve to the canonical production root above. If you start inside a Paperclip execution workspace, use absolute paths under the canonical production root for durable legal work products.
- Never write new work products under the forbidden root. If prior issue text points there, report BLOCKER_RUTA_CANONICA and write the corrected artifact under the canonical production root.

Before doing work, read these local contracts if available:
- skills/hermes-welaw-core/SKILL.md
- skills/hermes-welaw-paperclip/SKILL.md
- config/legal-worker-operating-contract.json
- config/welaw.yaml.example

LEGAL WORKER OPERATING CONTRACT:
- config/legal-worker-operating-contract.json is mandatory for real work.
- It controls google_docs_live_update, update_not_duplicate, cross_document_review, package_approval_payload, missing-info taxonomy, document states and WeasyPrint A4 editorial reference QA.
- If the contract cannot be read, post a blocker instead of improvising a reduced legal deliverable.

Use only synthetic data unless the issue explicitly names a real client record already present in the workspace.
Do not pipe curl into python or any interpreter.
Do not use `python -c`, heredocs, inline scripts, or ad hoc API scripts for Paperclip reads/writes; Hermes may block those commands.
Use the checked-in helper scripts from the canonical root exactly as commands, without wrapping them in `python -c`, pipes, heredocs, `export`, command substitution, or ad hoc scripts:
- Read issue as human text: `${PYTHON:-python3} runtime/scripts/pc_issue_brief.py ISSUE_ID`
- Read issue as JSON only if needed: `${PYTHON:-python3} runtime/scripts/pc_issue_detail.py ISSUE_ID`
- Post comment: `${PYTHON:-python3} runtime/scripts/pc_post_comment.py ISSUE_ID "COMMENT_BODY"`
- Mark done: `${PYTHON:-python3} runtime/scripts/pc_mark_done.py ISSUE_ID`
- List assigned issues only during no-task heartbeats: `${PYTHON:-python3} runtime/scripts/pc_list_issues.py --assignee {{{{agentId}}}} --limit 20`
Do not pipe helper output into `head`, `tail`, `python`, `jq`, `sed`, `grep`, or any interpreter/filter. Read the helper output directly.

Smoke tests:
- The HERMES LIVE OK workflow is allowed only when the assigned issue title or body explicitly says "live auth smoke" or "smoke test".
- For every other issue, follow the production contract above. Do not post HERMES LIVE OK for client or matter work.

{{{{#taskId}}}}
Assigned Paperclip issue:
- Issue ID: {{{{taskId}}}}
- Title: {{{{taskTitle}}}}

Issue body:
{{{{taskBody}}}}

Workflow:
1. Read the issue with `${PYTHON:-python3} runtime/scripts/pc_issue_brief.py {{{{taskId}}}}`.
2. Inspect the We Law skills/config listed above and any sources referenced by the issue.
3. If and only if this is an explicit live auth smoke issue, post a comment with the prefix "HERMES LIVE OK:" and include: agent name, role key, run id, files/skills inspected, and one concrete next operational action.
   Use `${PYTHON:-python3} runtime/scripts/pc_post_comment.py {{{{taskId}}}} "HERMES LIVE OK: <summary>"`.
4. For every real issue, execute the production contract and post the required production comment.
5. Mark the issue done only after the applicable completion gates pass:
   Use `${PYTHON:-python3} runtime/scripts/pc_mark_done.py {{{{taskId}}}}`.
6. End your response with the issue id and the words "Paperclip writeback confirmed" only when Paperclip was actually updated.
{{{{/taskId}}}}

{{{{#noTask}}}}
Heartbeat with no task:
1. List open issues assigned to you:
   `${PYTHON:-python3} runtime/scripts/pc_list_issues.py --assignee {{{{agentId}}}} --limit 20`
2. If an open issue exists, choose the highest priority not-done issue and save its id as ISSUE_ID.
3. Read ISSUE_ID:
   `${PYTHON:-python3} runtime/scripts/pc_issue_brief.py ISSUE_ID`
4. Read existing comments for ISSUE_ID. If a production completion comment already exists, do not reprocess that issue; leave a short final response saying it already has writeback evidence.
5. Inspect the We Law skills/config listed above and any sources referenced by the issue.
6. If and only if ISSUE_ID is an explicit live auth smoke issue, post a comment with the prefix "HERMES LIVE OK:" and include: agent name, role key, run id, files/skills inspected, and one concrete next operational action.
   Use `${PYTHON:-python3} runtime/scripts/pc_post_comment.py ISSUE_ID "HERMES LIVE OK: <summary>"`.
7. For every real issue, execute the production contract and post the required production comment.
8. Mark ISSUE_ID done only after the applicable completion gates pass:
   Use `${PYTHON:-python3} runtime/scripts/pc_mark_done.py ISSUE_ID`.
9. End your response with ISSUE_ID and the words "Paperclip writeback confirmed" only when Paperclip was actually updated.
10. If no issue exists, post no synthetic client data. Report what you checked.
{{{{/noTask}}}}
"""


class PaperclipApiError(RuntimeError):
    """Raised when Paperclip returns an API error."""


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_payloads(data: dict[str, Any], company_id: str | None = None) -> list[dict[str, Any]]:
    payloads = []
    runtime = data.get("runtime", {})
    api_url = str(data["paperclipApiUrl"]).rstrip("/")
    firm_model_path = ROOT / str(data.get("firmOperatingModel", "config/firm-operating-model.json"))
    firm_model = load_firm_model(firm_model_path)
    load_legal_worker_contract(LEGAL_WORKER_CONTRACT_PATH)
    validate_workers(firm_model, {str(worker["role"]): worker for worker in data["workers"]})
    for worker in data["workers"]:
        cwd = Path(str(runtime.get("cwd", str(ROOT))))
        resolved_cwd = str((ROOT / cwd).resolve() if not cwd.is_absolute() else cwd.resolve())
        payloads.append(
            {
                "method": "POST",
                "path": f"/api/companies/{company_id or '<company-id>'}/agents",
                "body": {
                    "name": worker["name"],
                    "adapterType": "hermes_local",
                    "adapterConfig": {
                        "persistSession": worker.get("persistSession", False),
                        "toolsets": worker["toolsets"],
                        "promptTemplate": build_live_prompt_template(worker, firm_model),
                        "paperclipApiUrl": api_url,
                        "hermesCommand": runtime.get("hermesCommand", DEFAULT_HERMES_COMMAND),
                        "cwd": resolved_cwd,
                        "timeoutSec": runtime.get("timeoutSec", 600),
                        "env": {
                            "PATH": runtime.get("path", DEFAULT_RUNTIME_PATH),
                            "PAPERCLIP_API_URL": api_url,
                        },
                    },
                    "metadata": {
                        "welawRole": worker["role"],
                        "skills": worker.get("skills", []),
                        "source": "hermes-we-law-os",
                    },
                },
            }
        )
    return payloads


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    origin: str | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if origin:
        headers["Origin"] = origin
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = request.Request(url, data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PaperclipApiError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise PaperclipApiError(f"{method} {url} -> {exc.reason}") from exc


def existing_agent_by_name(api_url: str, company_id: str, token: str | None, origin: str | None) -> dict[str, Any]:
    agents = request_json("GET", f"{api_url}/companies/{company_id}/agents", token=token, origin=origin)
    if not isinstance(agents, list):
        raise PaperclipApiError("GET agents did not return a list")
    return {str(agent.get("name")): agent for agent in agents if isinstance(agent, dict)}


def list_companies(api_url: str, token: str | None, origin: str | None) -> list[dict[str, Any]]:
    companies = request_json("GET", f"{api_url}/companies", token=token, origin=origin)
    if not isinstance(companies, list):
        raise PaperclipApiError("GET companies did not return a list")
    return [company for company in companies if isinstance(company, dict)]


def create_company(api_url: str, name: str, token: str | None, origin: str | None) -> dict[str, Any]:
    company = request_json(
        "POST",
        f"{api_url}/companies",
        token=token,
        origin=origin,
        body={
            "name": name,
            "description": "We Law S.C. runtime company managed by Hermes We Law OS.",
            "budgetMonthlyCents": 0,
        },
    )
    if not isinstance(company, dict) or not company.get("id"):
        raise PaperclipApiError("POST company did not return a company with id")
    return company


def resolve_company_id(
    api_url: str,
    *,
    company_id: str | None,
    company_name: str,
    create_if_missing: bool,
    token: str | None,
    origin: str | None,
) -> tuple[str, dict[str, Any] | None, str]:
    companies = list_companies(api_url, token, origin)
    if company_id:
        match = next((company for company in companies if company.get("id") == company_id), None)
        if match:
            return company_id, match, "found_by_id"
        if not create_if_missing:
            raise PaperclipApiError(f"Company not found: {company_id}")

    name_match = next((company for company in companies if company.get("name") == company_name), None)
    if name_match and isinstance(name_match.get("id"), str):
        return str(name_match["id"]), name_match, "found_by_name"

    if not create_if_missing:
        raise PaperclipApiError(f"Company not found by name: {company_name}")

    created = create_company(api_url, company_name, token, origin)
    return str(created["id"]), created, "created"


def apply_payloads(
    api_url: str,
    company_id: str,
    payloads: list[dict[str, Any]],
    *,
    token: str | None,
    origin: str | None,
    if_exists: str,
) -> list[dict[str, Any]]:
    api_url = api_url.rstrip("/")
    existing = existing_agent_by_name(api_url, company_id, token, origin)
    results: list[dict[str, Any]] = []
    for payload in payloads:
        body = payload["body"]
        name = str(body["name"])
        current = existing.get(name)
        if current and if_exists == "skip":
            results.append({"name": name, "action": "skipped", "id": current.get("id")})
            continue
        if current and if_exists == "error":
            raise PaperclipApiError(f"Agent already exists: {name}")
        if current and if_exists == "update":
            agent_id = current.get("id")
            updated = request_json("PATCH", f"{api_url}/agents/{agent_id}", token=token, origin=origin, body=body)
            results.append({"name": name, "action": "updated", "agent": updated})
            continue
        created = request_json(
            "POST",
            f"{api_url}/companies/{company_id}/agents",
            token=token,
            origin=origin,
            body=body,
        )
        results.append({"name": name, "action": "created", "agent": created})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without contacting Paperclip.")
    parser.add_argument("--apply", action="store_true", help="Create or update agents through the Paperclip API.")
    parser.add_argument("--api-url", default=None, help="Paperclip API URL, e.g. http://127.0.0.1:3100/api.")
    parser.add_argument("--company-id", default=None, help="Paperclip company UUID. Optional with --create-company.")
    parser.add_argument("--company-name", default="We Law S.C.", help="Company name used with --create-company.")
    parser.add_argument("--create-company", action="store_true", help="Create or reuse company by name when id is missing.")
    parser.add_argument("--token", default=os.environ.get("PAPERCLIP_API_TOKEN"), help="Optional Paperclip bearer token.")
    parser.add_argument("--origin", default=None, help="Optional trusted Origin header for board mutations.")
    parser.add_argument("--if-exists", choices=["skip", "update", "error"], default="skip")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        raise SystemExit("Use either --dry-run or --apply, not both.")

    data = load_config()
    api_url = (args.api_url or data["paperclipApiUrl"]).rstrip("/")
    payloads = build_payloads(data, args.company_id)
    if not args.apply:
        print(json.dumps({"dry_run": True, "api_url": api_url, "payloads": payloads}, indent=2, ensure_ascii=False))
        return 0

    try:
        company_id, company, company_action = resolve_company_id(
            api_url,
            company_id=args.company_id,
            company_name=args.company_name,
            create_if_missing=args.create_company,
            token=args.token,
            origin=args.origin,
        )
        payloads = build_payloads(data, company_id)
        results = apply_payloads(
            api_url,
            company_id,
            payloads,
            token=args.token,
            origin=args.origin,
            if_exists=args.if_exists,
        )
    except PaperclipApiError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "api_url": api_url,
                "company_id": company_id,
                "company_action": company_action,
                "company": company,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
