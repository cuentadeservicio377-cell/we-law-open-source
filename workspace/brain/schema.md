# Legal Brain Schema

Cada pagina usa frontmatter YAML simple, verdad compilada y timeline.

```markdown
---
type: matter
id: MAT-DEMO-001
client_id: CLI-001
aliases: []
status: activo
source_authority: user_direct_statement
updated_at: 2026-05-19
---

# Titulo

## Compiled Truth

Resumen actual, hechos confirmados, open threads y riesgos.

## See Also

- [Cliente](../clients/cli-001.md)

---

## Timeline

- **2026-05-19** | Source — Evento con cita.
```

## Page Requirements

- `clients/`: client id, canonical name, aliases, representantes, preferencias, riesgos, matters activos.
- `matters/`: MAT-ID, cliente, fase, documentos, fuentes, faltantes, tareas, aprobaciones, plazos.
- `processes/`: triggers, roles requeridos, artefactos, gates, dashboard state.
- `documents/`: tipo, estado, version, fuentes, placeholders, QA, links vivos.
- `law/`: jurisdiccion, materia, aplicabilidad, documentos relacionados, cautelas.
- `contradictions/`: fuentes en conflicto, impacto, decision pendiente, estado.

## Source Authority

1. User direct statement.
2. Google Workspace live file.
3. Paperclip issue/comment/approval.
4. Compiled brain truth.
5. Timeline entry.
6. Local workspace artifact.
7. External legal reference.
8. Agent inference.
