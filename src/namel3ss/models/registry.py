from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


MODELS_REGISTRY_FILENAME = "models_registry.yaml"


@dataclass(frozen=True)
class ModelRegistryEntry:
    name: str
    version: str
    provider: str
    domain: str
    tokens_per_second: float
    cost_per_token: float
    privacy_level: str
    status: str
    artifact_uri: str | None = None
    training_dataset_version: str | None = None
    metrics: dict[str, float] | None = None

    def ref(self) -> str:
        return f"{self.name}@{self.version}"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "domain": self.domain,
            "tokens_per_second": float(self.tokens_per_second),
            "cost_per_token": float(self.cost_per_token),
            "privacy_level": self.privacy_level,
            "status": self.status,
        }
        if self.artifact_uri:
            payload["artifact_uri"] = self.artifact_uri
        if self.training_dataset_version:
            payload["training_dataset_version"] = self.training_dataset_version
        if self.metrics:
            payload["metrics"] = {key: float(self.metrics[key]) for key in sorted(self.metrics.keys())}
        return payload


@dataclass(frozen=True)
class ModelRegistry:
    entries: tuple[ModelRegistryEntry, ...]

    def sorted_entries(self) -> tuple[ModelRegistryEntry, ...]:
        return tuple(sorted(self.entries, key=lambda entry: (entry.name, entry.version)))

    def find(self, reference: str) -> ModelRegistryEntry | None:
        name, version = _split_reference(reference)
        if version:
            for entry in self.entries:
                if entry.name == name and entry.version == version:
                    return entry
            return None
        candidates = [entry for entry in self.entries if entry.name == name]
        if not candidates:
            return None
        ordered = sorted(candidates, key=lambda entry: entry.version)
        return ordered[-1]

    def has_entries(self) -> bool:
        return bool(self.entries)


def models_registry_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / MODELS_REGISTRY_FILENAME


def load_model_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> ModelRegistry:
    path = models_registry_path(project_root, app_path)
    if path is None:
        if required:
            raise Namel3ssError(_missing_registry_message("models_registry.yaml"))
        return ModelRegistry(entries=())
    if not path.exists():
        if required:
            raise Namel3ssError(_missing_registry_message(path.as_posix()))
        return ModelRegistry(entries=())
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_registry_message(path, str(err))) from err
    entries = _parse_registry_payload(payload, path)
    return ModelRegistry(entries=tuple(entries))


def save_model_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    registry: ModelRegistry,
) -> Path:
    path = models_registry_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Model registry path could not be resolved.")
    payload = {"models": [entry.to_dict() for entry in registry.sorted_entries()]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def add_registry_entry(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
    provider: str,
    domain: str,
    tokens_per_second: float,
    cost_per_token: float,
    privacy_level: str,
    status: str = "active",
    artifact_uri: str | None = None,
    training_dataset_version: str | None = None,
    metrics: dict[str, float] | None = None,
) -> tuple[Path, ModelRegistryEntry]:
    entry = _normalize_entry(
        {
            "name": name,
            "version": version,
            "provider": provider,
            "domain": domain,
            "tokens_per_second": tokens_per_second,
            "cost_per_token": cost_per_token,
            "privacy_level": privacy_level,
            "status": status,
            "artifact_uri": artifact_uri,
            "training_dataset_version": training_dataset_version,
            "metrics": metrics or {},
        },
        path=models_registry_path(project_root, app_path) or Path(MODELS_REGISTRY_FILENAME),
    )
    registry = load_model_registry(project_root, app_path)
    for existing in registry.entries:
        if existing.name == entry.name and existing.version == entry.version:
            raise Namel3ssError(_duplicate_entry_message(entry.ref()))
    updated = ModelRegistry(entries=tuple(list(registry.entries) + [entry]))
    path = save_model_registry(project_root, app_path, updated)
    return path, entry


def deprecate_registry_entry(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
) -> tuple[Path, ModelRegistryEntry]:
    registry = load_model_registry(project_root, app_path, required=True)
    updated_entries: list[ModelRegistryEntry] = []
    deprecated: ModelRegistryEntry | None = None
    for entry in registry.entries:
        if entry.name == name and entry.version == version:
            deprecated = ModelRegistryEntry(
                name=entry.name,
                version=entry.version,
                provider=entry.provider,
                domain=entry.domain,
                tokens_per_second=entry.tokens_per_second,
                cost_per_token=entry.cost_per_token,
                privacy_level=entry.privacy_level,
                status="deprecated",
                artifact_uri=entry.artifact_uri,
                training_dataset_version=entry.training_dataset_version,
                metrics=entry.metrics,
            )
            updated_entries.append(deprecated)
            continue
        updated_entries.append(entry)
    if deprecated is None:
        raise Namel3ssError(_missing_entry_message(f"{name}@{version}"))
    path = save_model_registry(project_root, app_path, ModelRegistry(entries=tuple(updated_entries)))
    return path, deprecated


def resolve_model_entry(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    reference: str,
) -> ModelRegistryEntry | None:
    registry = load_model_registry(project_root, app_path)
    return registry.find(reference)


def _parse_registry_payload(payload: object, path: Path) -> list[ModelRegistryEntry]:
    if isinstance(payload, dict):
        values = payload.get("models", payload)
    else:
        values = payload
    if isinstance(values, dict):
        mapped: list[dict[str, object]] = []
        for name, versions in values.items():
            if isinstance(versions, list):
                for item in versions:
                    if not isinstance(item, dict):
                        raise Namel3ssError(_invalid_registry_message(path, "model entry must be a mapping"))
                    mapped_item = dict(item)
                    mapped_item.setdefault("name", name)
                    mapped.append(mapped_item)
            elif isinstance(versions, dict):
                mapped_item = dict(versions)
                mapped_item.setdefault("name", name)
                mapped.append(mapped_item)
            else:
                raise Namel3ssError(_invalid_registry_message(path, "model entry must be a mapping"))
        values = mapped
    if not isinstance(values, list):
        raise Namel3ssError(_invalid_registry_message(path, "models must be a list or map"))
    entries: list[ModelRegistryEntry] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, dict):
            raise Namel3ssError(_invalid_registry_message(path, "model entry must be a mapping"))
        entry = _normalize_entry(raw, path=path)
        if entry.ref() in seen:
            raise Namel3ssError(_duplicate_entry_message(entry.ref()))
        seen.add(entry.ref())
        entries.append(entry)
    entries.sort(key=lambda item: (item.name, item.version))
    return entries


def _normalize_entry(raw: dict[str, object], *, path: Path) -> ModelRegistryEntry:
    name = _required_text(raw.get("name"), path, "name")
    version = _required_version(raw.get("version"), path)
    provider = _required_text(raw.get("provider"), path, "provider")
    domain = _required_text(raw.get("domain"), path, "domain")
    tokens_per_second = _required_number(raw.get("tokens_per_second"), path, "tokens_per_second")
    cost_per_token = _required_number(raw.get("cost_per_token"), path, "cost_per_token")
    privacy_level = _required_text(raw.get("privacy_level"), path, "privacy_level")
    status = _required_text(raw.get("status", "active"), path, "status").lower()
    artifact_uri = _optional_text(raw.get("artifact_uri"), path=path, field="artifact_uri")
    training_dataset_version = _optional_text(
        raw.get("training_dataset_version"),
        path=path,
        field="training_dataset_version",
    )
    metrics = _optional_metrics(raw.get("metrics"), path=path)
    if status not in {"active", "deprecated"}:
        raise Namel3ssError(_invalid_registry_message(path, "status must be active or deprecated"))
    return ModelRegistryEntry(
        name=name,
        version=version,
        provider=provider,
        domain=domain,
        tokens_per_second=tokens_per_second,
        cost_per_token=cost_per_token,
        privacy_level=privacy_level,
        status=status,
        artifact_uri=artifact_uri,
        training_dataset_version=training_dataset_version,
        metrics=metrics,
    )


def _required_text(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_invalid_registry_message(path, f"{field} is required"))
    return value.strip()


def _required_version(value: object, path: Path) -> str:
    if isinstance(value, str):
        if value.strip():
            return value.strip()
        raise Namel3ssError(_invalid_registry_message(path, "version is required"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    raise Namel3ssError(_invalid_registry_message(path, "version is required"))


def _required_number(value: object, path: Path, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise Namel3ssError(_invalid_registry_message(path, f"{field} must be a number"))
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_registry_message(path, f"{field} must be a number")) from err
    if parsed < 0:
        raise Namel3ssError(_invalid_registry_message(path, f"{field} must be non-negative"))
    return parsed


def _optional_text(value: object, *, path: Path, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise Namel3ssError(_invalid_registry_message(path, f"{field} must be text"))
    text = value.strip()
    return text if text else None


def _optional_metrics(value: object, *, path: Path) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_registry_message(path, "metrics must be a mapping"))
    metrics: dict[str, float] = {}
    for key in sorted(value.keys()):
        raw = value.get(key)
        if isinstance(raw, bool):
            continue
        try:
            metrics[str(key)] = float(raw)
        except Exception as err:
            raise Namel3ssError(_invalid_registry_message(path, f"metrics.{key} must be a number")) from err
    return metrics


def _split_reference(reference: str) -> tuple[str, str | None]:
    text = str(reference or "").strip()
    if "@" in text:
        name, version = text.split("@", 1)
        return name.strip(), version.strip() or None
    if ":" in text:
        name, version = text.rsplit(":", 1)
        if name.strip() and version.strip():
            return name.strip(), version.strip()
    return text, None


def _missing_registry_message(path: str) -> str:
    return build_guidance_message(
        what="Model registry file is missing.",
        why=f"Expected {path}.",
        fix="Create models_registry.yaml with at least one active model entry.",
        example=(
            "models:\n"
            "  - name: gpt-4\n"
            "    version: \"1.0\"\n"
            "    provider: openai\n"
            "    domain: general\n"
            "    tokens_per_second: 50\n"
            "    cost_per_token: 0.00001\n"
            "    privacy_level: standard\n"
            "    status: active"
        ),
    )


def _invalid_registry_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Model registry is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Use a deterministic models list with required fields.",
        example=(
            "models:\n"
            "  - name: gpt-4\n"
            "    version: \"1.0\"\n"
            "    provider: openai\n"
            "    domain: general\n"
            "    tokens_per_second: 50\n"
            "    cost_per_token: 0.00001\n"
            "    privacy_level: standard\n"
            "    status: active"
        ),
    )


def _duplicate_entry_message(reference: str) -> str:
    return build_guidance_message(
        what=f"Model registry has a duplicate entry for {reference}.",
        why="Each name and version pair must be unique.",
        fix="Keep one entry per model version.",
        example="gpt-4@1.0",
    )


def _missing_entry_message(reference: str) -> str:
    return build_guidance_message(
        what=f"Model {reference} was not found in models_registry.yaml.",
        why="The requested model version is not registered.",
        fix="Add the model with n3 models add or use an existing version.",
        example=f"n3 models add {reference.split('@', 1)[0]} {reference.split('@', 1)[1]} --provider openai --domain general --tokens-per-second 10 --cost-per-token 0.1 --privacy-level standard",
    )


__all__ = [
    "MODELS_REGISTRY_FILENAME",
    "ModelRegistry",
    "ModelRegistryEntry",
    "add_registry_entry",
    "deprecate_registry_entry",
    "load_model_registry",
    "models_registry_path",
    "resolve_model_entry",
    "save_model_registry",
]
