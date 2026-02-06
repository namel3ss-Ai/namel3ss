from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.simple_yaml import parse_yaml


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

SPEC_GRAMMAR_DIR = Path(__file__).resolve().parents[3] / "spec" / "grammar"
SPEC_REGISTRY_FILE = SPEC_GRAMMAR_DIR / "registry.yaml"


@dataclass(frozen=True)
class SpecVersion:
    version: str
    grammar_file: str
    overview_file: str
    released_at: int

    @property
    def grammar_path(self) -> Path:
        return SPEC_GRAMMAR_DIR.parents[1] / self.grammar_file

    @property
    def overview_path(self) -> Path:
        return SPEC_GRAMMAR_DIR.parents[1] / self.overview_file


@dataclass(frozen=True)
class SpecRegistry:
    versions: tuple[SpecVersion, ...]

    def sorted_versions(self) -> tuple[SpecVersion, ...]:
        return tuple(sorted(self.versions, key=lambda item: (_semver_key(item.version), item.version)))

    def latest(self) -> SpecVersion | None:
        ordered = self.sorted_versions()
        return ordered[-1] if ordered else None

    def find(self, version: str) -> SpecVersion | None:
        target = str(version or "").strip()
        for item in self.versions:
            if item.version == target:
                return item
        return None


def spec_registry_path() -> Path:
    return SPEC_REGISTRY_FILE


def load_spec_registry(path: Path | None = None) -> SpecRegistry:
    target = path or SPEC_REGISTRY_FILE
    if not target.exists():
        raise Namel3ssError(_missing_registry_message(target))
    try:
        payload = parse_yaml(target.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_registry_message(target, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_registry_message(target, "top-level value must be a map"))
    rows = payload.get("versions")
    if not isinstance(rows, list) or not rows:
        raise Namel3ssError(_invalid_registry_message(target, "versions must be a non-empty list"))
    versions: list[SpecVersion] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise Namel3ssError(_invalid_registry_message(target, "each version entry must be a map"))
        version = _require_semver(row.get("version"), field_name="version")
        if version in seen:
            raise Namel3ssError(_invalid_registry_message(target, f"version '{version}' is duplicated"))
        seen.add(version)
        grammar_file = _require_text(row.get("grammar_file"), field_name="grammar_file")
        overview_file = _require_text(row.get("overview_file"), field_name="overview_file")
        released_at = _require_int(row.get("released_at"), field_name="released_at")
        item = SpecVersion(
            version=version,
            grammar_file=grammar_file,
            overview_file=overview_file,
            released_at=released_at,
        )
        _validate_spec_files(item, target)
        versions.append(item)
    return SpecRegistry(versions=tuple(versions))


def resolve_spec_version(version: str | None) -> SpecVersion:
    registry = load_spec_registry()
    if version is None or not str(version).strip():
        latest = registry.latest()
        if latest is None:
            raise Namel3ssError(_missing_versions_message())
        return latest
    target = registry.find(str(version))
    if target is None:
        raise Namel3ssError(_unknown_version_message(str(version), registry))
    return target


def latest_spec_version() -> SpecVersion:
    latest = load_spec_registry().latest()
    if latest is None:
        raise Namel3ssError(_missing_versions_message())
    return latest


def read_spec_grammar(version: str | None = None) -> str:
    spec = resolve_spec_version(version)
    return spec.grammar_path.read_text(encoding="utf-8")


def _validate_spec_files(item: SpecVersion, registry_path: Path) -> None:
    root = registry_path.parents[2]
    grammar_path = root / item.grammar_file
    overview_path = root / item.overview_file
    if not grammar_path.exists():
        raise Namel3ssError(_invalid_registry_message(registry_path, f"missing grammar file {item.grammar_file}"))
    if not overview_path.exists():
        raise Namel3ssError(_invalid_registry_message(registry_path, f"missing overview file {item.overview_file}"))


def _semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _require_text(value: object, *, field_name: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_invalid_field_message(field_name))


def _require_semver(value: object, *, field_name: str) -> str:
    text = _require_text(value, field_name=field_name)
    if not _SEMVER_RE.match(text):
        raise Namel3ssError(_invalid_semver_message(field_name, text))
    return text


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_field_message(field_name))
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_field_message(field_name)) from err
    if parsed < 0:
        raise Namel3ssError(_invalid_field_message(field_name))
    return parsed


def _missing_registry_message(path: Path) -> str:
    return build_guidance_message(
        what="Spec registry is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Add spec/grammar/registry.yaml.",
        example="versions:\n  - version: 1.0.0\n    grammar_file: spec/grammar/v1.0.0/namel3ss.grammar\n    overview_file: spec/grammar/v1.0.0/overview.md\n    released_at: 1",
    )


def _invalid_registry_message(path: Path, detail: str) -> str:
    return build_guidance_message(
        what="Spec registry is invalid.",
        why=f"{path.as_posix()} could not be loaded: {detail}.",
        fix="Fix the registry file and ensure all referenced files exist.",
        example="version: 1.0.0",
    )


def _invalid_field_message(field_name: str) -> str:
    return build_guidance_message(
        what=f"Spec registry field '{field_name}' is invalid.",
        why=f"'{field_name}' is missing or malformed.",
        fix=f"Set a valid value for '{field_name}'.",
        example=f"{field_name}: value",
    )


def _invalid_semver_message(field_name: str, value: str) -> str:
    return build_guidance_message(
        what=f"Spec registry field '{field_name}' is invalid.",
        why=f"Expected semantic version major.minor.patch, got '{value}'.",
        fix="Use a semantic version like 1.0.0.",
        example="version: 1.0.0",
    )


def _missing_versions_message() -> str:
    return build_guidance_message(
        what="No spec versions are defined.",
        why="spec/grammar/registry.yaml has no versions.",
        fix="Add at least one spec version entry.",
        example="version: 1.0.0",
    )


def _unknown_version_message(version: str, registry: SpecRegistry) -> str:
    available = ", ".join(item.version for item in registry.sorted_versions()) or "none"
    return build_guidance_message(
        what=f'Spec version "{version}" is not available.',
        why=f"Available versions: {available}.",
        fix="Use one of the available versions or add a new version entry.",
        example=f"Known versions: {available}",
    )


__all__ = [
    "SPEC_GRAMMAR_DIR",
    "SPEC_REGISTRY_FILE",
    "SpecRegistry",
    "SpecVersion",
    "latest_spec_version",
    "load_spec_registry",
    "read_spec_grammar",
    "resolve_spec_version",
    "spec_registry_path",
]
