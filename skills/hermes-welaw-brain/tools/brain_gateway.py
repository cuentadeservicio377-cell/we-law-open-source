"""Gateway for the We Law Legal Brain.

The gateway prefers a configured `gbrain` CLI when available, but keeps a
deterministic local markdown fallback so Hermes can reason before external
indexing is installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BRAIN_ROOT = ROOT / "workspace/brain"


@dataclass(frozen=True)
class BrainEngineStatus:
    preferred: str
    available: bool
    path: str | None
    fallback: str


def detect_engine() -> BrainEngineStatus:
    path = shutil.which("gbrain")
    return BrainEngineStatus(
        preferred="gbrain",
        available=bool(path),
        path=path,
        fallback="local_markdown",
    )


class LocalBrainGateway:
    def __init__(self, root: str | Path = DEFAULT_BRAIN_ROOT):
        self.root = Path(root)

    def page_path(self, domain: str, slug: str) -> Path:
        safe_domain = slugify(domain)
        safe_slug = slugify(slug)
        return self.root / safe_domain / f"{safe_slug}.md"

    def write_page(
        self,
        domain: str,
        slug: str,
        *,
        title: str,
        compiled_truth: str,
        frontmatter: dict[str, Any] | None = None,
        timeline: list[dict[str, str]] | None = None,
    ) -> Path:
        path = self.page_path(domain, slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {"type": domain, "updated_at": str(date.today()), **(frontmatter or {})}
        body = render_page(title=title, frontmatter=fm, compiled_truth=compiled_truth, timeline=timeline or [])
        path.write_text(body, encoding="utf-8")
        return path

    def read_page(self, domain: str, slug: str) -> str:
        path = self.page_path(domain, slug)
        return path.read_text(encoding="utf-8")

    def search(self, query: str, *, domains: list[str] | None = None, limit: int = 10) -> list[dict[str, Any]]:
        tokens = [token for token in re.split(r"\W+", normalize(query)) if len(token) >= 3]
        if not tokens:
            return []
        candidates: list[Path] = []
        if domains:
            for domain in domains:
                candidates.extend((self.root / slugify(domain)).glob("*.md"))
        else:
            candidates = list(self.root.glob("*/*.md"))

        results = []
        for path in candidates:
            text = path.read_text(encoding="utf-8", errors="replace")
            normalized = normalize(text)
            score = sum(normalized.count(token) for token in tokens)
            if score:
                results.append(
                    {
                        "path": str(path),
                        "domain": path.parent.name,
                        "slug": path.stem,
                        "score": score,
                        "title": extract_title(text) or path.stem,
                        "snippet": snippet(text, tokens),
                    }
                )
        return sorted(results, key=lambda item: (-item["score"], item["path"]))[:limit]


def render_page(
    *,
    title: str,
    frontmatter: dict[str, Any],
    compiled_truth: str,
    timeline: list[dict[str, str]],
) -> str:
    fm = "\n".join(f"{key}: {value}" for key, value in frontmatter.items())
    lines = [
        "---",
        fm,
        "---",
        "",
        f"# {title}",
        "",
        "## Compiled Truth",
        "",
        compiled_truth.strip() or "Sin verdad compilada.",
        "",
        "---",
        "",
        "## Timeline",
        "",
    ]
    if not timeline:
        lines.append(f"- **{date.today()}** | Source: brain_gateway — Pagina creada.")
    else:
        for entry in timeline:
            lines.append(f"- **{entry.get('date', date.today())}** | {entry.get('source', 'Source')} — {entry.get('summary', '')}")
    lines.append("")
    return "\n".join(lines)


def extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def snippet(text: str, tokens: list[str]) -> str:
    normalized = normalize(text)
    first = min((normalized.find(token) for token in tokens if token in normalized), default=0)
    start = max(0, first - 80)
    end = min(len(text), first + 180)
    return " ".join(text[start:end].split())


def slugify(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "untitled"


def normalize(value: str) -> str:
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
    }
    result = value.lower()
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result
