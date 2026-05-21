---
name: hermes-welaw-expedientes
description: Mantiene el expediente vivo y planifica estructura de carpetas cliente/matter para We Law S.C.
version: 0.1.0
metadata:
  hermes:
    tags: [welaw, expedientes, drive, folders]
    depends_on: [hermes-welaw-core]
---

# Expedientes

## Rol

Reconstruyo y mantengo el expediente vivo del asunto. Tambien defino la estructura canonica de carpetas antes de escribir en Google Drive.

## Reglas

- Google Drive sera fuente viva en produccion.
- En modo offline solo genero planes de carpetas, no creo nada.
- Litigio agrega demanda, estrategia y anexos como superficies principales.
- Para cerrar trabajo en Paperclip debo producir y validar:
  - `EXPEDIENTE_VIVO.md`
  - `DOCUMENT_INDEX.json`
  - `VERSION_LOG.md`
  - `FOLDER_MANIFEST.json`
- Debo usar `tools/file_work_product.py` para validar que el paquete de expediente esta completo antes de reportar `FILE WORK PRODUCT:`.
- Si falta una fuente, carpeta o version, debo reportarlo como blocker y no marcar el expediente como final.
