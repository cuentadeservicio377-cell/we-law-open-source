# We Law Legal Brain Index

Este cerebro es la capa comun de razonamiento de Hermes y Paperclip.

## Capas

- Institucional: `processes/`, `playbooks/`, `law/`, `templates/`, `clauses/`, `risks/`, `lessons/`.
- Cliente/Matter: `clients/`, `matters/`, `people/`, `organizations/`, `meetings/`, `transcripts/`, `documents/`, `evidence/`.
- Operativa: `deadlines/`, `approvals/`, `billing/`, `contradictions/`, `inbox/`.

## Estado

- Engine preferido: `gbrain`.
- Fallback actual: markdown local + busqueda por texto.
- Regla: brain-first antes de delegar a Paperclip.
