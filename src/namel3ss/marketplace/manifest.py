from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


MANIFEST_FILE = "manifest.yaml"
ALT_MANIFEST_FILE = "capability.yaml"
ALLOWED_TYPES = {"prompt", "dataset", "flow", "plugin", "template"}


@dataclass(frozen=True)
class MarketplaceItemManifest:
    name: str
    version: str
    item_type: str
    description: str
    author: str
    license: str
    files: tuple[str, ...]
    requirements: tuple[str, ...]
    dependencies: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "version": self.version,
            "type": self.item_type,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "files": list(self.files),
        }
        if self.dependencies:
            payload["dependencies"] = list(self.dependencies)
        if self.requirements:
            payload["requirements"] = list(self.requirements)
        return payload



def manifest_path_for(item_path: str | Path) -> Path:
    path = Path(item_path)
    if path.is_dir():
        primary = path / MANIFEST_FILE
        if primary.exists():
            return primary
        alternative = path / ALT_MANIFEST_FILE
        if alternative.exists():
            return alternative
        return primary
    return path



def load_manifest(item_path: str | Path) -> tuple[MarketplaceItemManifest, Path]:
    manifest_path = manifest_path_for(item_path)
    if not manifest_path.exists():
        raise Namel3ssError(_missing_manifest_message(manifest_path))
    try:
        payload = parse_yaml(manifest_path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_manifest_message(manifest_path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_manifest_message(manifest_path, "expected a YAML map"))

    manifest = MarketplaceItemManifest(
        name=_required_text(payload.get("name"), "name", manifest_path),
        version=_required_text(payload.get("version"), "version", manifest_path),
        item_type=_required_type(payload.get("type"), manifest_path),
        description=_required_text(payload.get("description"), "description", manifest_path),
        author=_required_text(payload.get("author"), "author", manifest_path),
        license=_required_text(payload.get("license"), "license", manifest_path),
        files=_required_files(payload.get("files"), manifest_path),
        requirements=_optional_dependencies(payload.get("requirements"), manifest_path),
        dependencies=_optional_dependencies(payload.get("dependencies"), manifest_path),
    )
    if not manifest.requirements and manifest.dependencies:
        manifest = MarketplaceItemManifest(
            name=manifest.name,
            version=manifest.version,
            item_type=manifest.item_type,
            description=manifest.description,
            author=manifest.author,
            license=manifest.license,
            files=manifest.files,
            requirements=manifest.dependencies,
            dependencies=manifest.dependencies,
        )
    if manifest.requirements and not manifest.dependencies:
        manifest = MarketplaceItemManifest(
            name=manifest.name,
            version=manifest.version,
            item_type=manifest.item_type,
            description=manifest.description,
            author=manifest.author,
            license=manifest.license,
            files=manifest.files,
            requirements=manifest.requirements,
            dependencies=manifest.requirements,
        )
    return manifest, manifest_path.parent.resolve()



def write_manifest(path: Path, manifest: MarketplaceItemManifest) -> None:
    path.write_text(render_yaml(manifest.to_dict()), encoding="utf-8")



def validate_manifest_files(manifest: MarketplaceItemManifest, item_root: Path) -> list[str]:
    missing: list[str] = []
    for relative in manifest.files:
        target = (item_root / relative).resolve()
        if not _inside(item_root.resolve(), target):
            missing.append(relative)
            continue
        if not target.exists() or target.is_dir():
            missing.append(relative)
    return sorted(missing)



def _required_text(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_invalid_manifest_message(path, f"{field} is required"))
    return value.strip()



def _required_type(value: object, path: Path) -> str:
    raw = _required_text(value, "type", path)
    if raw not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        raise Namel3ssError(_invalid_manifest_message(path, f"type must be one of: {allowed}"))
    return raw



def _required_files(value: object, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise Namel3ssError(_invalid_manifest_message(path, "files must be a non-empty list"))
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise Namel3ssError(_invalid_manifest_message(path, "files entries must be text"))
        relative = item.strip().replace("\\", "/")
        if relative.startswith("/") or relative.startswith("../") or "/../" in relative:
            raise Namel3ssError(_invalid_manifest_message(path, "files entries must be project-relative"))
        cleaned.append(relative)
    deduped = sorted(set(cleaned))
    return tuple(deduped)



def _optional_dependencies(value: object, path: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise Namel3ssError(_invalid_manifest_message(path, "dependencies must be a list"))
    cleaned = [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]
    return tuple(sorted(set(cleaned)))



def _inside(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
    except ValueError:
        return False
    return True



def _missing_manifest_message(path: Path) -> str:
    return build_guidance_message(
        what="Marketplace manifest is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Create manifest.yaml or capability.yaml with required metadata.",
        example=(
            "name: demo.item\n"
            "version: 0.1.0\n"
            "type: flow\n"
            "description: Demo flow\n"
            "author: team\n"
            "license: MIT\n"
            "files:\n"
            "  - app.ai"
        ),
    )



def _invalid_manifest_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Marketplace manifest is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Update manifest fields and retry.",
        example=(
            "name: demo.item\n"
            "version: 0.1.0\n"
            "type: flow\n"
            "description: Demo flow\n"
            "author: team\n"
            "license: MIT\n"
            "files:\n"
            "  - app.ai"
        ),
    )


__all__ = [
    "ALLOWED_TYPES",
    "ALT_MANIFEST_FILE",
    "MANIFEST_FILE",
    "MarketplaceItemManifest",
    "load_manifest",
    "manifest_path_for",
    "validate_manifest_files",
    "write_manifest",
]
