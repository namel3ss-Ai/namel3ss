from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError


_PACK_DIRS: tuple[str, ...] = (
    "huggingface",
    "local_runner",
    "vision_gen",
    "speech",
    "third_party_apis",
)
_SUPPORTED_MODES = {"text", "image", "audio"}


@dataclass(frozen=True)
class ProviderMetadata:
    name: str
    capability_token: str
    supported_modes: tuple[str, ...]
    models: tuple[str, ...]

    def has_model(self, model_identifier: str) -> bool:
        return model_identifier in self.models

    def supports_mode(self, mode: str) -> bool:
        token = str(mode or "text").strip().lower()
        if token == "structured":
            token = "text"
        return token in self.supported_modes


def list_provider_metadata() -> tuple[ProviderMetadata, ...]:
    return tuple(_metadata_map().values())


def provider_pack_names() -> tuple[str, ...]:
    return tuple(sorted(_metadata_map().keys()))


def get_provider_metadata(name: str) -> ProviderMetadata | None:
    return _metadata_map().get(str(name or "").strip().lower())


def capability_for_provider(name: str) -> str | None:
    metadata = get_provider_metadata(name)
    if metadata is None:
        return None
    return metadata.capability_token


def provider_name_for_model(model_identifier: str) -> str | None:
    text = str(model_identifier or "").strip()
    if ":" not in text:
        return None
    prefix = text.split(":", 1)[0].strip().lower()
    if prefix in _metadata_map():
        return prefix
    return None


def validate_model_identifier(
    *,
    model_identifier: str,
    provider_name: str,
) -> None:
    metadata = get_provider_metadata(provider_name)
    if metadata is None:
        return
    model_text = str(model_identifier or "").strip()
    if not model_text.startswith(f"{metadata.name}:"):
        example = metadata.models[0] if metadata.models else f"{metadata.name}:model"
        raise Namel3ssError(
            f"Provider '{metadata.name}' requires namespaced model identifiers. Example: {example}"
        )
    if metadata.has_model(model_text):
        return
    suggestions = ", ".join(metadata.models[:3])
    raise Namel3ssError(
        f"Unknown model '{model_text}' for provider '{metadata.name}'. Try one of: {suggestions}"
    )


def model_supports_mode(*, model_identifier: str, mode: str) -> bool:
    provider_name = provider_name_for_model(model_identifier)
    if provider_name is None:
        return True
    metadata = get_provider_metadata(provider_name)
    if metadata is None:
        return True
    return metadata.supports_mode(mode)


def _metadata_map() -> dict[str, ProviderMetadata]:
    if not hasattr(_metadata_map, "_cache"):
        payload: dict[str, ProviderMetadata] = {}
        root = Path(__file__).resolve().parent
        for pack_dir in _PACK_DIRS:
            manifest_path = root / pack_dir / "pack_manifest.json"
            metadata = _parse_manifest(manifest_path)
            payload[metadata.name] = metadata
        setattr(_metadata_map, "_cache", payload)
    return dict(getattr(_metadata_map, "_cache"))


def _parse_manifest(path: Path) -> ProviderMetadata:
    if not path.exists():
        raise Namel3ssError(f"Provider pack manifest missing: {path.as_posix()}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(f"Provider pack manifest is invalid JSON: {path.as_posix()}") from err
    if not isinstance(payload, dict):
        raise Namel3ssError(f"Provider pack manifest must be an object: {path.as_posix()}")

    name = _required_text(payload.get("name"), path=path, field="name")
    capability_token = _required_text(payload.get("capability_token"), path=path, field="capability_token")
    supported_modes = _required_list(payload.get("supported_modes"), path=path, field="supported_modes")
    models = _required_list(payload.get("models"), path=path, field="models")

    mode_tokens = tuple(sorted({item.strip().lower() for item in supported_modes if item.strip()}))
    if not mode_tokens or any(item not in _SUPPORTED_MODES for item in mode_tokens):
        raise Namel3ssError(
            f"Provider pack manifest {path.as_posix()} has unsupported modes. Use: text, image, audio"
        )

    normalized_models = tuple(sorted({item.strip() for item in models if item.strip()}))
    if not normalized_models:
        raise Namel3ssError(f"Provider pack manifest {path.as_posix()} must define at least one model")

    return ProviderMetadata(
        name=name.strip().lower(),
        capability_token=capability_token.strip().lower(),
        supported_modes=mode_tokens,
        models=normalized_models,
    )


def _required_text(value: object, *, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(f"Provider pack manifest {path.as_posix()} is missing '{field}'")
    return value


def _required_list(value: object, *, path: Path, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise Namel3ssError(f"Provider pack manifest {path.as_posix()} is missing '{field}'")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise Namel3ssError(f"Provider pack manifest {path.as_posix()} field '{field}' contains invalid entries")
        output.append(item)
    return tuple(output)


__all__ = [
    "ProviderMetadata",
    "capability_for_provider",
    "get_provider_metadata",
    "list_provider_metadata",
    "model_supports_mode",
    "provider_name_for_model",
    "provider_pack_names",
    "validate_model_identifier",
]
