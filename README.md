# We Law Open Source

We Law Open Source is a public, sanitized legal-operations reference system based on the research and experimentation of WSC.Lat and We Law. It explores how a lawyer can supervise a legal office where Hermes coordinates the work, Paperclip tracks specialized legal workers, Google Workspace remains the familiar office layer, and a dashboard gives the human lawyer certainty about what is happening.

This is not an "AI lawyer in a box". It is an architecture for lawyer-controlled legal operations: agents can help only when source evidence, memory, worker contracts, review gates, blockers and human approvals are visible.

## What It Combines

- **Dashboard trust surface:** the lawyer and Hermes coexist in one command center for clients, matters, documents, missing information, deadlines, approvals, Workspace state and Paperclip activity.
- **Hermes Managing Partner:** Hermes receives instructions, resolves client/matter context, reads the Legal Brain, routes work, asks for missing information and prepares partner briefings.
- **Paperclip legal staff:** 14 role-based workers behave like a legal office staff, each with skills, tools, required artifacts and completion gates.
- **Google Workspace office layer:** Drive, Docs, Sheets, Calendar, Tasks and communications are treated as the office where work lives. The public repo ships demo fixtures instead of live credentials.
- **Legal Brain:** a local-first memory model for clients, matters, processes, templates, risks, deadlines, clauses and lessons learned.
- **Command Spine:** every instruction becomes a command record, matter brief, delegation plan, Workspace manifest, worker context package, approval gate and partner briefing.

## The 14 Legal Workers

1. **Despacho Legal:** Managing legal office coordinator. Owns the matter, reads the Legal Brain, checks Workspace and Paperclip state, creates delegation plans, keeps blockers visible and prepares the partner briefing.
2. **Recepcionista Juridico / Intake:** Handles client and matter intake from conversations, folders and forms. Identifies existing clients, opens new matters, extracts missing information and prepares intake packets.
3. **Expediente / Records Manager:** Maintains the live matter file, source index, folder manifest, evidence provenance, version log and matter history.
4. **Data Clerk Google Sheets:** Maintains structured ledgers for clients, matters, facts, documents, missing information, approvals, billing references and workspace manifests.
5. **Analista Juridico:** Maps facts to legal issues, identifies legal risks, summarizes applicable rules and prepares analysis notes for drafting and review.
6. **Documentos Legales:** Drafts and updates legal documents with evidence maps, data ledgers, correction logs, placeholder reports, manifests and legal QA.
7. **Privacidad y Compliance:** Reviews privacy, data protection, confidentiality, consent, records handling and compliance risks.
8. **IP Software:** Handles software, copyright, licensing, ownership, SaaS, source code and technology-contract issues.
9. **Litigio:** Builds case theory, evidence lists, procedural checklists, pleadings support, filing blockers and court deadline dependencies.
10. **Plazos:** Owns deadline extraction, conservative deadline ledgers, reminders, uncertainty flags and escalation state.
11. **Cobranza:** Tracks fee, retainer, invoice, payment, authorization and commercial blockers.
12. **Produccion Editorial:** Turns reviewed legal work into polished packages and checks formatting, completeness, exhibit order and readability.
13. **Revisor Senior:** Acts as the senior legal quality gate before partner approval, delivery, filing or signature.
14. **Admin Biblioteca / Knowledge Manager:** Curates templates, playbooks, clause libraries, process notes, lessons learned and Legal Brain update proposals.

## Quickstart

```bash
git clone https://github.com/cuentadeservicio377-cell/we-law-open-source.git <!-- public-safety: allow -->
cd we-law-open-source
python3 scripts/public_safety_scan.py
bash scripts/test.sh
cd dashboard
npm install
npm run build
NEXT_PUBLIC_DEMO_MODE=true npm run dev -- --hostname 127.0.0.1 --port 3012
```

Open http://127.0.0.1:3012 and review the synthetic Northstar Health Demo matter.

## Demo Data

The repository includes fake demo transcripts, fake matter records, fake Workspace manifests and fake Paperclip issue summaries. They are intentionally blocked at the senior-review gate to show the most important behavior: the system must stop honestly when facts, cross-document review or signature data are missing.

## Live Integrations

The public repo is offline-first. Live Hermes, Paperclip and Google Workspace integrations are optional and must be enabled with environment variables in `.env.example`. Never commit tokens, client documents or real Workspace exports.

## How The Community Can Help

We need help with legal workflow modeling, dashboard UX for non-technical lawyers, safe memory design, Paperclip worker contracts, Google Workspace adapters, synthetic legal fixtures, document QA, privacy/security review, template libraries, jurisdiction packs and tests that catch shallow agent behavior.

## Lessons Learned

- Chat-only legal agents lose trust when the lawyer cannot see sources, blockers and status.
- Legal drafting agents over-compress documents unless governed by evidence maps and review gates.
- "Done" is meaningless without artifacts, QA, missing-info classification and approval state.
- Workspace matters because lawyers already understand folders, docs, sheets, calendars and tasks.
- Worker specialization needs tools, output contracts and senior review, not only prompts.
- Legal memory must be client-aware, matter-aware and auditable.

## Disclaimer

This project is research and tooling. It is not legal advice, does not create an attorney-client relationship and does not replace professional legal judgment. A licensed lawyer must review and approve all client-facing work.
