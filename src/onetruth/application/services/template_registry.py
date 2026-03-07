from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_TEMPLATE_REGISTRY_PATH = (
    REPO_ROOT / "fixtures/workflows/schedule_planning/template_registry.v1.yaml"
)


@dataclass(frozen=True)
class TemplateRecord:
    template_id: str
    workflow_id: str
    stage_id: str
    dataset_key: str
    variant: str
    media_type: str
    source_path: Path
    description: str

    def as_public_dict(self) -> dict[str, Any]:
        relative_path = str(self.source_path.relative_to(REPO_ROOT))
        return {
            "template_id": self.template_id,
            "workflow_id": self.workflow_id,
            "stage_id": self.stage_id,
            "dataset_key": self.dataset_key,
            "artifact_kind": self.dataset_key,
            "variant": self.variant,
            "media_type": self.media_type,
            "file_path": relative_path,
            "file_name": self.source_path.name,
            "description": self.description,
        }


@dataclass(frozen=True)
class TemplateRegistry:
    workflow_id: str
    version: int
    manifest_path: Path
    templates: tuple[TemplateRecord, ...]

    def template_by_id(self, template_id: str) -> TemplateRecord:
        for item in self.templates:
            if item.template_id == template_id:
                return item
        raise ValueError(f"template_id not found: {template_id}")


def load_template_registry(path: Path | None = None) -> TemplateRegistry:
    manifest_path = (path or DEFAULT_TEMPLATE_REGISTRY_PATH).resolve()
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("template registry manifest must be a mapping")

    registry = raw.get("registry")
    if not isinstance(registry, dict):
        raise ValueError("template registry manifest missing 'registry' mapping")

    workflow_id = str(registry.get("workflow_id") or "").strip()
    version = int(registry.get("version") or 0)
    if not workflow_id:
        raise ValueError("template registry workflow_id is required")
    if version <= 0:
        raise ValueError("template registry version must be positive")

    raw_templates = registry.get("templates")
    if not isinstance(raw_templates, list):
        raise ValueError("template registry templates must be a list")

    templates: list[TemplateRecord] = []
    seen_template_ids: set[str] = set()
    for item in raw_templates:
        if not isinstance(item, dict):
            raise ValueError("template registry entries must be mappings")
        template_id = str(item.get("template_id") or "").strip()
        if not template_id:
            raise ValueError("template entry missing template_id")
        if template_id in seen_template_ids:
            raise ValueError(f"duplicate template_id in registry: {template_id}")
        seen_template_ids.add(template_id)

        source_path = _resolve_source_path(item.get("source_path"))
        templates.append(
            TemplateRecord(
                template_id=template_id,
                workflow_id=workflow_id,
                stage_id=str(item.get("stage_id") or "").strip(),
                dataset_key=str(item.get("dataset_key") or "").strip(),
                variant=str(item.get("variant") or "").strip(),
                media_type=str(item.get("media_type") or "").strip(),
                source_path=source_path,
                description=str(item.get("description") or "").strip(),
            )
        )

    return TemplateRegistry(
        workflow_id=workflow_id,
        version=version,
        manifest_path=manifest_path,
        templates=tuple(templates),
    )


def list_templates(
    *,
    registry: TemplateRegistry | None = None,
    workflow_id: str | None = None,
    stage_id: str | None = None,
    dataset_key: str | None = None,
    variant: str | None = None,
) -> list[dict[str, Any]]:
    active_registry = registry or load_template_registry()
    filtered: list[dict[str, Any]] = []
    for item in active_registry.templates:
        if workflow_id is not None and item.workflow_id != workflow_id:
            continue
        if stage_id is not None and item.stage_id != stage_id:
            continue
        if dataset_key is not None and item.dataset_key != dataset_key:
            continue
        if variant is not None and item.variant != variant:
            continue
        filtered.append(item.as_public_dict())
    return filtered


def _resolve_source_path(raw_path: Any) -> Path:
    if raw_path is None:
        raise ValueError("template entry source_path is required")
    source = Path(str(raw_path))
    if not source.is_absolute():
        source = (REPO_ROOT / source).resolve()
    if not source.exists() or not source.is_file():
        raise ValueError(f"template source_path does not exist: {source}")
    source.relative_to(REPO_ROOT)
    return source
