#!/usr/bin/env python3
"""Offline 14-role legal-firm regression smoke for Hermes We Law OS."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/hermes-welaw-core/tools"))
sys.path.insert(0, str(ROOT / "skills/hermes-welaw-intake/tools"))

from control_master import build_control_master_update
from firm_model import load_firm_model
from legal_knowledge import required_reviewers_for_package
from transcript_intake import build_transcript_intake


def run_smoke() -> dict:
    firm_model = load_firm_model(ROOT / "config/firm-operating-model.json")
    transcript_intake = build_transcript_intake(
        [
            {
                "id": "TRANS-001",
                "title": "Llamada inicial MAT-DEMO-001",
                "url": "local://fixtures/mat005/trans-001",
                "text": """
                Cliente: Clínica Demo S.A. de C.V.
                Proyecto: plataforma para venta de servicios entre médicos y pacientes.
                Necesitamos términos y condiciones, aviso de privacidad, aviso para médicos y pacientes,
                formato ARCO, NDA para desarrolladores, contrato de desarrollo de software y convenio
                de cotitularidad.
                """,
            },
            {
                "id": "TRANS-002",
                "title": "Correcciones primera entrega",
                "url": "local://fixtures/mat005/trans-002",
                "text": """
                Corrección: el aviso debe distinguir pacientes y médicos.
                Corrección: el contrato de desarrollo debe aclarar entregables, repositorio y propiedad intelectual.
                Falta confirmar RFC, domicilio de firma y representante legal.
                """,
            },
        ]
    )
    client = {"id": "CLI-SMOKE", "nombre": transcript_intake["client"]["name"], "estado": "activo"}
    matter = {
        "id": "MAT-DEMO-001",
        "client_id": client["id"],
        "cliente": client["nombre"],
        "tipo": "contractual",
        "estado": "activo",
        "descripcion": transcript_intake["matter"]["description"],
        "fase": "documental",
    }
    control = build_control_master_update(
        {
            "client": client,
            "matter": matter,
            "sources": [
                {"id": "TRANS-001", "title": "Llamada inicial MAT-DEMO-001", "url": "local://fixtures/mat005/trans-001"},
                {"id": "TRANS-002", "title": "Correcciones primera entrega", "url": "local://fixtures/mat005/trans-002"},
            ],
            "transcript_intake": transcript_intake,
            "tasks": build_role_handoff_tasks(matter["id"], transcript_intake["required_documents"]),
            "approvals": [{"id": "APR-SMOKE", "type": "package", "status": "pending"}],
            "deliverables": [
                {"id": f"DEL-{index:03d}", "document_type": doc_type, "status": "draft"}
                for index, doc_type in enumerate(transcript_intake["required_documents"], start=1)
            ],
        }
    )
    blockers = [item["field"] for item in transcript_intake["missing_info"]]
    reviewers = required_reviewers_for_package(transcript_intake["required_documents"])
    return {
        "ok": len(firm_model["roles"]) == 14 and len(transcript_intake["required_documents"]) == 7,
        "role_count": len(firm_model["roles"]),
        "matter_id": matter["id"],
        "package": {
            "required_documents": len(transcript_intake["required_documents"]),
            "documents": transcript_intake["required_documents"],
            "reviewers": reviewers,
        },
        "handoffs": build_handoffs(reviewers),
        "control_master_tables": list(control["tables"]),
        "control_row_counts": {table: len(rows) for table, rows in control["tables"].items()},
        "blockers": blockers,
        "senior_review": {
            "decision": "blocked" if blockers else "client-deliverable",
            "reason": "Missing signature/fiscal data blocks signature-ready status." if blockers else "Synthetic package has no blockers.",
        },
        "live_bootstrap": {
            "paperclip_mutated": False,
            "google_workspace_mutated": False,
            "next_command": "python3 runtime/scripts/bootstrap-paperclip-workers.py --apply --if-exists update only after runtime and credentials are healthy",
        },
    }


def build_role_handoff_tasks(matter_id: str, document_types: list[str]) -> list[dict]:
    return [
        {"id": "TRA-SMOKE-001", "matter_id": matter_id, "title": "Indexar carpeta fuente", "owner": "Expediente"},
        {"id": "TRA-SMOKE-002", "matter_id": matter_id, "title": "Actualizar control maestro", "owner": "Data Clerk / Google Sheets"},
        {"id": "TRA-SMOKE-003", "matter_id": matter_id, "title": "Preparar base juridica", "owner": "Analista Juridico"},
        {
            "id": "TRA-SMOKE-004",
            "matter_id": matter_id,
            "title": f"Redactar paquete de {len(document_types)} documentos",
            "owner": "Documentos Legales",
        },
        {"id": "TRA-SMOKE-005", "matter_id": matter_id, "title": "Revision privacidad", "owner": "Privacidad y Compliance"},
        {"id": "TRA-SMOKE-006", "matter_id": matter_id, "title": "Revision software/IP", "owner": "IP / Software"},
        {"id": "TRA-SMOKE-007", "matter_id": matter_id, "title": "Revision senior", "owner": "Revisor Senior"},
    ]


def build_handoffs(reviewers: list[str]) -> list[dict]:
    return [{"from": "master", "to": role, "status": "planned"} for role in reviewers]


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
