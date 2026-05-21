"""Legal brain maintenance / dream-cycle checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def inspect_brain(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    domains = [path for path in root.iterdir() if path.is_dir()] if root.exists() else []
    markdown_pages = [path for path in root.glob("*/*.md") if path.name != "README.md"] if root.exists() else []
    contradictions = list((root / "contradictions").glob("*.md")) if (root / "contradictions").exists() else []
    inbox = list((root / "inbox").glob("*.md")) if (root / "inbox").exists() else []
    orphan_pages = [
        str(path)
        for path in markdown_pages
        if path.parent.name not in {"clients", "matters", "processes", "law", "documents", "evidence"}
        and "## Timeline" not in path.read_text(encoding="utf-8", errors="replace")
    ]
    return {
        "ok": root.exists(),
        "domain_count": len(domains),
        "page_count": len(markdown_pages),
        "contradiction_count": len(contradictions),
        "inbox_count": len(inbox),
        "orphan_count": len(orphan_pages),
        "stale_count": 0,
        "orphan_pages": orphan_pages,
        "recommended_actions": build_recommendations(len(inbox), len(contradictions), len(orphan_pages)),
    }


def build_recommendations(inbox_count: int, contradiction_count: int, orphan_count: int) -> list[str]:
    actions = []
    if inbox_count:
        actions.append("Clasificar entradas en inbox.")
    if contradiction_count:
        actions.append("Resolver contradicciones abiertas con fuente de autoridad.")
    if orphan_count:
        actions.append("Normalizar paginas sin timeline.")
    if not actions:
        actions.append("Brain sano para operacion local.")
    return actions
