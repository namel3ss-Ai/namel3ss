from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


DATASET_REGISTRY_FILENAME = "dataset_registry.yaml"
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class DatasetVersion:
    dataset_name: str
    version: str
    schema: tuple[tuple[str, str], ...]
    source: str
    transformations: tuple[str, ...]
    owner: str | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "version": self.version,
            "schema": {field: type_name for field, type_name in self.schema},
            "source": self.source,
        }
        if self.transformations:
            payload["transformations"] = list(self.transformations)
        if self.owner:
            payload["owner"] = self.owner
        return payload


@dataclass(frozen=True)
class DatasetRecord:
    name: str
    versions: tuple[DatasetVersion, ...]

    def sorted_versions(self) -> tuple[DatasetVersion, ...]:
        return tuple(sorted(self.versions, key=lambda item: (_version_sort_key(item.version), item.version)))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "versions": [entry.to_dict() for entry in self.sorted_versions()],
        }


@dataclass(frozen=True)
class DatasetRegistry:
    datasets: tuple[DatasetRecord, ...]

    def sorted_datasets(self) -> tuple[DatasetRecord, ...]:
        return tuple(sorted(self.datasets, key=lambda item: item.name))

    def find(self, name: str) -> DatasetRecord | None:
        text = str(name or "").strip()
        for dataset in self.datasets:
            if dataset.name == text:
                return dataset
        return None


def dataset_registry_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / DATASET_REGISTRY_FILENAME


def load_dataset_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> DatasetRegistry:
    path = dataset_registry_path(project_root, app_path)
    if path is None:
        if required:
            raise Namel3ssError(_missing_registry_message("dataset_registry.yaml"))
        return DatasetRegistry(datasets=())
    if not path.exists():
        if required:
            raise Namel3ssError(_missing_registry_message(path.as_posix()))
        return DatasetRegistry(datasets=())
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_registry_message(path, str(err))) from err
    datasets = _parse_registry_payload(payload, path)
    return DatasetRegistry(datasets=tuple(sorted(datasets, key=lambda item: item.name)))


def save_dataset_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    registry: DatasetRegistry,
) -> Path:
    path = dataset_registry_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Dataset registry path could not be resolved.")
    payload = {"datasets": [entry.to_dict() for entry in registry.sorted_datasets()]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def add_dataset_version(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    dataset_name: str,
    version: str,
    schema: dict[str, str],
    source: str,
    transformations: list[str] | tuple[str, ...] | None = None,
    owner: str | None = None,
) -> tuple[Path, DatasetVersion]:
    normalized_name = _required_text(dataset_name, "dataset name")
    normalized_version = _required_version(version)
    normalized_schema = _normalize_schema(schema)
    normalized_source = _required_text(source, "source")
    normalized_owner = _optional_text(owner)
    normalized_transformations = _normalize_transformations(transformations or [])

    registry = load_dataset_registry(project_root, app_path)
    datasets = list(registry.datasets)
    existing = registry.find(normalized_name)
    new_entry = DatasetVersion(
        dataset_name=normalized_name,
        version=normalized_version,
        schema=normalized_schema,
        source=normalized_source,
        transformations=normalized_transformations,
        owner=normalized_owner,
    )
    if existing is None:
        datasets.append(DatasetRecord(name=normalized_name, versions=(new_entry,)))
    else:
        for item in existing.versions:
            if item.version == normalized_version:
                raise Namel3ssError(_duplicate_version_message(normalized_name, normalized_version))
        updated_versions = list(existing.versions)
        updated_versions.append(new_entry)
        updated_record = DatasetRecord(name=existing.name, versions=tuple(updated_versions))
        datasets = [updated_record if item.name == existing.name else item for item in datasets]
    path = save_dataset_registry(project_root, app_path, DatasetRegistry(datasets=tuple(datasets)))
    return path, new_entry


def dataset_history(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    dataset_name: str,
) -> tuple[DatasetVersion, ...]:
    registry = load_dataset_registry(project_root, app_path, required=True)
    record = registry.find(dataset_name)
    if record is None:
        raise Namel3ssError(_missing_dataset_message(dataset_name))
    return record.sorted_versions()


def parse_schema_arg(raw: str) -> dict[str, str]:
    text = str(raw or "").strip()
    if not text:
        raise Namel3ssError(_invalid_schema_message("schema is required"))
    values: dict[str, str] = {}
    for part in text.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise Namel3ssError(_invalid_schema_message(f"schema entry '{chunk}' must use field:type"))
        field, type_name = chunk.split(":", 1)
        field_name = field.strip()
        type_value = type_name.strip()
        if not field_name or not type_value:
            raise Namel3ssError(_invalid_schema_message(f"schema entry '{chunk}' is invalid"))
        values[field_name] = type_value
    if not values:
        raise Namel3ssError(_invalid_schema_message("schema is required"))
    return values


def _parse_registry_payload(payload: object, path: Path) -> list[DatasetRecord]:
    if isinstance(payload, dict):
        values = payload.get("datasets", payload)
    else:
        values = payload
    rows: list[dict[str, object]] = []
    if isinstance(values, dict):
        for dataset_name, item in values.items():
            if isinstance(item, list):
                rows.append({"name": dataset_name, "versions": item})
                continue
            if isinstance(item, dict):
                item_payload = dict(item)
                item_payload.setdefault("name", dataset_name)
                rows.append(item_payload)
                continue
            raise Namel3ssError(_invalid_registry_message(path, f"dataset '{dataset_name}' must be a mapping"))
    elif isinstance(values, list):
        for item in values:
            if not isinstance(item, dict):
                raise Namel3ssError(_invalid_registry_message(path, "dataset entry must be a mapping"))
            rows.append(item)
    else:
        raise Namel3ssError(_invalid_registry_message(path, "datasets must be a list or map"))

    records: list[DatasetRecord] = []
    seen_names: set[str] = set()
    for row in rows:
        name = _required_text(row.get("name"), "dataset name")
        if name in seen_names:
            raise Namel3ssError(_invalid_registry_message(path, f"dataset '{name}' is duplicated"))
        seen_names.add(name)
        dataset_owner = _optional_text(row.get("owner"))
        versions_raw = row.get("versions")
        if isinstance(versions_raw, dict):
            versions_raw = [versions_raw]
        if not isinstance(versions_raw, list):
            raise Namel3ssError(_invalid_registry_message(path, f"dataset '{name}' must include versions"))
        versions: list[DatasetVersion] = []
        seen_versions: set[str] = set()
        for version_raw in versions_raw:
            if not isinstance(version_raw, dict):
                raise Namel3ssError(_invalid_registry_message(path, f"dataset '{name}' version entry must be a mapping"))
            entry = _normalize_dataset_version(version_raw, dataset_name=name, default_owner=dataset_owner)
            if entry.version in seen_versions:
                raise Namel3ssError(_duplicate_version_message(name, entry.version))
            seen_versions.add(entry.version)
            versions.append(entry)
        records.append(DatasetRecord(name=name, versions=tuple(versions)))
    return records


def _normalize_dataset_version(
    raw: dict[str, object],
    *,
    dataset_name: str,
    default_owner: str | None,
) -> DatasetVersion:
    version = _required_version(raw.get("version"))
    schema = _normalize_schema(raw.get("schema"))
    source = _required_text(raw.get("source"), "source")
    transformations = _normalize_transformations(raw.get("transformations"))
    owner = _optional_text(raw.get("owner")) or default_owner
    return DatasetVersion(
        dataset_name=dataset_name,
        version=version,
        schema=schema,
        source=source,
        transformations=transformations,
        owner=owner,
    )


def _normalize_schema(raw: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, dict):
        raise Namel3ssError(_invalid_schema_message("schema must be a map of field:type"))
    values: list[tuple[str, str]] = []
    for key in sorted(raw.keys()):
        field_name = _required_text(key, "schema field")
        type_name = _required_text(raw.get(key), f"schema type for '{field_name}'")
        values.append((field_name, type_name))
    if not values:
        raise Namel3ssError(_invalid_schema_message("schema must include at least one field"))
    return tuple(values)


def _normalize_transformations(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise Namel3ssError(_invalid_transformations_message("transformations must be a list"))
    values: list[str] = []
    for item in raw:
        text = _required_text(item, "transformation")
        values.append(text)
    return tuple(values)


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise Namel3ssError(f"{field} is required.")
    return text


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _required_version(value: object) -> str:
    text = _required_text(value, "version")
    if not _SEMVER_RE.match(text):
        raise Namel3ssError(
            build_guidance_message(
                what="Dataset version is invalid.",
                why=f'Expected semantic version "major.minor.patch", got "{text}".',
                fix="Use a semantic version like 1.0.0.",
                example="n3 dataset add-version faq-dataset 1.1.0 --source faq_upload --schema question:text,answer:text",
            )
        )
    return text


def _version_sort_key(value: str) -> tuple[int, int, int]:
    if not _SEMVER_RE.match(value):
        return (0, 0, 0)
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _missing_registry_message(path: str) -> str:
    return build_guidance_message(
        what="Dataset registry file is missing.",
        why=f"Expected {path}.",
        fix="Create dataset_registry.yaml or add a version with n3 dataset add-version.",
        example="n3 dataset add-version faq-dataset 1.0.0 --source faq_upload --schema question:text,answer:text",
    )


def _invalid_registry_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Dataset registry is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Use deterministic dataset entries with versions, schema, and source.",
        example=(
            "datasets:\n"
            "  - name: faq-dataset\n"
            "    versions:\n"
            "      - version: 1.0.0\n"
            "        schema:\n"
            "          question: text\n"
            "          answer: text\n"
            "        source: faq_upload_2026_01"
        ),
    )


def _invalid_schema_message(details: str) -> str:
    return build_guidance_message(
        what="Dataset schema is invalid.",
        why=details,
        fix="Define schema with one or more field:type pairs.",
        example="--schema question:text,answer:text",
    )


def _invalid_transformations_message(details: str) -> str:
    return build_guidance_message(
        what="Dataset transformations are invalid.",
        why=details,
        fix="Provide transformations as repeated --transform flags.",
        example="--transform \"removed empty answers\"",
    )


def _duplicate_version_message(dataset_name: str, version: str) -> str:
    return build_guidance_message(
        what=f"Dataset {dataset_name} already has version {version}.",
        why="Each dataset version must be unique.",
        fix="Use a new semantic version when adding lineage updates.",
        example=f"n3 dataset add-version {dataset_name} 1.0.1 --source upload_2 --schema question:text,answer:text",
    )


def _missing_dataset_message(dataset_name: str) -> str:
    return build_guidance_message(
        what=f'Dataset "{dataset_name}" was not found.',
        why="The dataset is missing from dataset_registry.yaml.",
        fix="Add a version for this dataset first.",
        example=f"n3 dataset add-version {dataset_name} 1.0.0 --source upload_1 --schema question:text,answer:text",
    )


__all__ = [
    "DATASET_REGISTRY_FILENAME",
    "DatasetRecord",
    "DatasetRegistry",
    "DatasetVersion",
    "add_dataset_version",
    "dataset_history",
    "dataset_registry_path",
    "load_dataset_registry",
    "parse_schema_arg",
    "save_dataset_registry",
]
