"""Local legal template registry for Hermes We Law OS."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = ROOT / "workspace/templates/legal/manifest.json"
TOKEN_RE = re.compile(r"\{\{([a-zA-Z0-9_.-]+)\}\}")


@dataclass(frozen=True)
class TemplateRecord:
    id: str
    title: str
    area: str
    document_type: str
    path: str
    variables: list[str]
    status: str = "draft"
    drive_ready: bool = True
    owner: str = "Admin Biblioteca"
    jurisdiction: str = "MX"
    review_status: str = "draft"
    last_reviewed_at: str | None = None
    required_variables: list[str] | None = None


@dataclass(frozen=True)
class TemplateQualityValidation:
    ok: bool
    invalid: list[str]


class TemplateRegistry:
    def __init__(self, manifest_path: str | Path = DEFAULT_MANIFEST):
        self.manifest_path = Path(manifest_path)
        self.root = self.manifest_path.parent

    def load(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {
                "version": "0.1.0",
                "source": "local",
                "drive_ready": True,
                "root": str(self.root),
                "templates": [],
            }
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save(self, manifest: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def list_templates(self, area: str | None = None, document_type: str | None = None) -> list[dict[str, Any]]:
        templates = list(self.load().get("templates", []))
        if area:
            templates = [item for item in templates if item.get("area") == area]
        if document_type:
            templates = [item for item in templates if item.get("document_type") == document_type]
        return templates

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        for item in self.list_templates():
            if item.get("id") == template_id:
                return item
        return None

    def register_template(
        self,
        template_id: str,
        title: str,
        area: str,
        document_type: str,
        path: str | Path,
        status: str = "draft",
        *,
        owner: str = "Admin Biblioteca",
        jurisdiction: str = "MX",
        review_status: str = "draft",
        last_reviewed_at: str | None = None,
        required_variables: list[str] | None = None,
    ) -> dict[str, Any]:
        path = Path(path)
        absolute = path if path.is_absolute() else ROOT / path
        if not absolute.exists():
            raise FileNotFoundError(f"Template not found: {path}")

        try:
            rel = absolute.relative_to(ROOT).as_posix()
        except ValueError:
            rel = absolute.as_posix()
        record = TemplateRecord(
            id=template_id,
            title=title,
            area=area,
            document_type=document_type,
            path=rel,
            variables=extract_variables(absolute.read_text(encoding="utf-8")),
            status=status,
            owner=owner,
            jurisdiction=jurisdiction,
            review_status=review_status,
            last_reviewed_at=last_reviewed_at,
            required_variables=required_variables or extract_variables(absolute.read_text(encoding="utf-8")),
        )
        manifest = self.load()
        templates = [item for item in manifest.get("templates", []) if item.get("id") != template_id]
        templates.append(record.__dict__)
        templates.sort(key=lambda item: item["id"])
        manifest["templates"] = templates
        self.save(manifest)
        return record.__dict__

    def import_local_folder(
        self,
        folder: str | Path,
        *,
        area: str,
        owner: str,
        jurisdiction: str = "MX",
    ) -> list[dict[str, Any]]:
        root = Path(folder)
        imported = []
        for path in sorted(root.glob("*.md")):
            document_type = slugify(path.stem)
            template_id = next_template_id(self.load(), area)
            imported.append(
                self.register_template(
                    template_id,
                    title_from_stem(path.stem),
                    area,
                    document_type,
                    path,
                    owner=owner,
                    jurisdiction=jurisdiction,
                    review_status="draft",
                )
            )
        return imported

    def context_for_paperclip(self) -> dict[str, Any]:
        templates = self.list_templates()
        return {
            "template_registry": str(self.manifest_path.relative_to(ROOT)),
            "templates": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "area": item["area"],
                    "document_type": item["document_type"],
                    "variables": item.get("variables", []),
                    "path": item["path"],
                    "owner": item.get("owner"),
                    "jurisdiction": item.get("jurisdiction"),
                    "review_status": item.get("review_status"),
                }
                for item in templates
            ],
        }


def extract_variables(content: str) -> list[str]:
    return sorted(set(TOKEN_RE.findall(content)))


def validate_template_quality(manifest: dict[str, Any]) -> TemplateQualityValidation:
    invalid: list[str] = []
    areas = set(manifest.get("areas", []))
    for item in manifest.get("templates", []):
        template_id = item.get("id", "<missing-id>")
        for key in ["owner", "jurisdiction", "review_status", "last_reviewed_at"]:
            if key not in item:
                invalid.append(f"{template_id} missing {key}")
        if areas and item.get("area") not in areas:
            invalid.append(f"{template_id} area is not registered")
        if item.get("review_status") not in {"needs_template", "draft", "review", "approved", "deprecated", None}:
            invalid.append(f"{template_id} has invalid review_status")
        required = item.get("required_variables", [])
        if required and not isinstance(required, list):
            invalid.append(f"{template_id} required_variables must be a list")
    return TemplateQualityValidation(ok=not invalid, invalid=invalid)


def slugify(value: str) -> str:
    text = value.lower().strip().replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return re.sub(r"_+", "_", text).strip("_") or "template"


def title_from_stem(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip().title()


def next_template_id(manifest: dict[str, Any], area: str) -> str:
    prefix = f"TPL-{area[:3].upper()}"
    existing = [
        item.get("id", "")
        for item in manifest.get("templates", [])
        if str(item.get("id", "")).startswith(prefix)
    ]
    return f"{prefix}-{len(existing) + 1:03d}"


def register_template(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return TemplateRegistry().register_template(*args, **kwargs)
