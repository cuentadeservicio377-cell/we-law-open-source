"""Minimal markdown document renderer for We Law."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


TOKEN_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"
PACKAGE_DOCUMENTS = {
    "mat005_software_health_platform": [
        "terminos_condiciones",
        "aviso_privacidad_integral",
        "aviso_privacidad_medicos_pacientes",
        "formato_arco",
        "nda",
        "contrato_desarrollo_software",
        "convenio_cotitularidad",
    ],
    "software_health_platform": [
        "terminos_condiciones",
        "aviso_privacidad_integral",
        "aviso_privacidad_medicos_pacientes",
        "formato_arco",
        "nda",
        "contrato_desarrollo_software",
        "convenio_cotitularidad",
    ],
}


@dataclass
class RenderedDocument:
    content: str
    missing_variables: list[str]
    status: str
    version: str


class DocumentEngine:
    def __init__(self, template_root: str | Path = TEMPLATE_ROOT):
        self.template_root = Path(template_root)

    def render(
        self,
        template_name: str,
        variables: dict[str, Any],
        version: str = "v1",
        faltantes_para_firma: list[str] | None = None,
    ) -> RenderedDocument:
        template = self._read_template(template_name)
        variables = {**variables, "version": version}
        missing = sorted({token for token in TOKEN_RE.findall(template) if not variables.get(token)})

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            value = variables.get(key)
            return str(value) if value not in (None, "") else f"[PENDIENTE: {key}]"

        content = TOKEN_RE.sub(replace, template)
        signature_missing = faltantes_para_firma or []
        status = "borrador"
        if version == "final" and not missing and not signature_missing:
            status = "final"
        elif version == "final":
            status = "revision"

        return RenderedDocument(content, missing + signature_missing, status, version)

    def _read_template(self, template_name: str) -> str:
        path = self.template_root / f"{template_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        return path.read_text(encoding="utf-8")


def required_package_documents(package_type: str) -> list[str]:
    try:
        return list(PACKAGE_DOCUMENTS[package_type])
    except KeyError as exc:
        raise ValueError(f"Unknown document package: {package_type}") from exc
