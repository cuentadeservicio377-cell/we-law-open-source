"""Billing and work authorization ledger for We Law."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = (
    "BILLING_LEDGER.json",
    "WORK_AUTHORIZATION_STATUS.md",
    "BILLING_QA.md",
)


@dataclass
class BillingLedgerValidation:
    ok: bool
    missing_files: list[str]
    invalid_files: list[str]
    blockers: list[str]


def build_billing_record(
    *,
    matter_id: str,
    quote_amount: float,
    retainer_required: float,
    payments: list[dict[str, Any]],
    invoice_status: str,
    engagement_status: str,
) -> dict[str, Any]:
    paid_amount = sum(float(payment.get("amount", 0)) for payment in payments)
    balance = max(float(quote_amount) - paid_amount, 0)
    stop_work_triggers = stop_work_reasons(
        retainer_required=retainer_required,
        paid_amount=paid_amount,
        engagement_status=engagement_status,
    )
    return {
        "matter_id": matter_id,
        "quote_amount": quote_amount,
        "retainer_required": retainer_required,
        "payments": payments,
        "paid_amount": paid_amount,
        "balance": balance,
        "invoice_status": invoice_status,
        "engagement_status": engagement_status,
        "work_authorized": not stop_work_triggers,
        "stop_work_triggers": stop_work_triggers,
    }


def validate_billing_ledger(workspace: str | Path) -> BillingLedgerValidation:
    root = Path(workspace)
    missing = [name for name in REQUIRED_ARTIFACTS if not (root / name).exists()]
    invalid: list[str] = []
    blockers: list[str] = []

    ledger = _read_json(root / "BILLING_LEDGER.json", invalid)
    if isinstance(ledger, dict):
        for key in ["matter_id", "quote_amount", "paid_amount", "balance", "invoice_status", "engagement_status"]:
            if key not in ledger:
                invalid.append(f"BILLING_LEDGER.json missing {key}")
        if ledger.get("work_authorized") is not True:
            blockers.append("work is not financially authorized")
    elif ledger is not None:
        invalid.append("BILLING_LEDGER.json must be an object")

    _require_nonempty(root / "WORK_AUTHORIZATION_STATUS.md", invalid)
    _require_nonempty(root / "BILLING_QA.md", invalid)

    return BillingLedgerValidation(
        ok=not missing and not invalid and not blockers,
        missing_files=missing,
        invalid_files=invalid,
        blockers=blockers,
    )


def stop_work_reasons(*, retainer_required: float, paid_amount: float, engagement_status: str) -> list[str]:
    reasons = []
    if engagement_status != "approved":
        reasons.append("engagement_not_approved")
    if retainer_required > 0 and paid_amount < retainer_required:
        reasons.append("retainer_missing")
    return reasons


def _read_json(path: Path, invalid: list[str]) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        invalid.append(f"{path.name} invalid JSON: {exc.msg}")
        return None


def _require_nonempty(path: Path, invalid: list[str]) -> None:
    if path.exists() and not path.read_text(encoding="utf-8").strip():
        invalid.append(f"{path.name} is empty")
