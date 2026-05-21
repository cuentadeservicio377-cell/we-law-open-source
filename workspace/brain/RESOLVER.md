# We Law Legal Brain Resolver

Antes de crear o actualizar una pagina del cerebro, identifica el sujeto primario. El formato no decide la carpeta; el sujeto juridico-operativo decide la carpeta.

## Decision

1. Cliente canónico, aliases, preferencias, riesgos generales -> `clients/`.
2. Asunto especifico con MAT-ID, fase, open threads, estado documental -> `matters/`.
3. Persona natural: representante, contacto, contraparte, medico, desarrollador -> `people/`.
4. Empresa u organizacion: cliente moral, proveedor, contraparte, autoridad -> `organizations/`.
5. Reunion o llamada completa -> `meetings/`.
6. Transcripcion fuente -> `transcripts/`.
7. Documento legal o entregable -> `documents/`.
8. Hecho, fuente, prueba, evidencia o matriz factual -> `evidence/`.
9. Proceso operativo reusable -> `processes/`.
10. Playbook o SOP de puesto -> `playbooks/`.
11. Ley, regla, criterio, articulo o requisito juridico -> `law/`.
12. Jurisdiccion, materia, autoridad o competencia -> `jurisdictions/`.
13. Juzgado, tribunal, autoridad o calendario oficial -> `courts/`.
14. Plazo, computo, recordatorio o agenda -> `deadlines/`.
15. Plantilla, variable o manifest de template -> `templates/`.
16. Clausula reusable o biblioteca contractual -> `clauses/`.
17. Riesgo legal, operativo, financiero o de entrega -> `risks/`.
18. Aprobacion viva o gate humano -> `approvals/`.
19. Cobranza, honorarios, anticipo, abono o cierre financiero -> `billing/`.
20. Leccion aprendida, mejora o propuesta de biblioteca -> `lessons/`.
21. Contradiccion entre fuentes, documentos o memoria -> `contradictions/`.
22. Si no hay casa clara -> `inbox/` y crear open thread para clasificar.

## Reglas

- Un hecho durable necesita fuente: `[Source: tipo, detalle, YYYY-MM-DD]`.
- La verdad compilada vive arriba de `---`.
- La timeline vive abajo de `---` y es append-only.
- Las contradicciones no se borran; se resuelven con fuente y fecha.
- Un worker de Paperclip no escribe verdad institucional directa. Produce `BRAIN_UPDATE_PROPOSAL.json`.
