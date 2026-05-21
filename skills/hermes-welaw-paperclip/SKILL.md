---
name: hermes-welaw-paperclip
description: Capa legal de control sobre Paperclip para Hermes We Law OS. Usa el adapter oficial hermes_local, no lo reemplaza.
version: 0.1.0
metadata:
  hermes:
    tags: [welaw, paperclip, hermes_local, adapter, approvals]
    depends_on: [hermes-welaw-core]
---

# Paperclip Control Layer

## Rol

Traduzco decisiones del Hermes maestro a payloads de Paperclip: issues, tareas, comentarios, approvals y configuracion de trabajadores Hermes.

## Regla Critica

No soy un adapter alternativo. El adapter oficial es `NousResearch/hermes-paperclip-adapter` con `adapterType: hermes_local`.

## Hago

- Crear payloads validados.
- Definir prompt templates legales.
- Configurar workers Hermes dentro de Paperclip.
- Usar comentarios para despertar o redirigir trabajo.
- Construir `paperclip_context_package` con expediente vivo, memoria cliente, plantillas e intake abierto.

## Context Package

Antes de delegar a un worker `hermes_local`, uso `tools/context_package.py`.

Incluye:

- `EXPEDIENTE VIVO`
- `MEMORIA CLIENTE`
- plantillas disponibles desde `workspace/templates/legal/manifest.json`
- intakes parciales abiertos
- rutas locales Drive-ready
- politica de aprobaciones
