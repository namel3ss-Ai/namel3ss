from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.runtime.ai.providers.provider_pack_catalog import provider_pack_catalog
from namel3ss.runtime.providers.pack_registry import get_provider_metadata, validate_model_identifier


SETTINGS_SCHEMA_VERSION = 1
SETTINGS_DIR = ".namel3ss"
SETTINGS_FILENAME = "provider_settings.json"


def get_providers_payload(source: str, app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    settings_path = _settings_path(app_file)
    settings = _load_settings(settings_path)

    ai_providers = {
        str(getattr(ai, "provider", "") or "").strip().lower()
        for ai in project.program.ais.values()
        if str(getattr(ai, "provider", "") or "").strip()
    }

    providers: list[dict[str, object]] = []
    for item in provider_pack_catalog():
        provider_name = str(item.get("name") or "").strip().lower()
        provider_models = list(item.get("models") or [])
        saved = settings.get(provider_name, {})
        default_model = str(saved.get("default_model") or "")
        secret_name = str(saved.get("secret_name") or "")
        if not default_model and provider_models:
            default_model = str(provider_models[0])
        providers.append(
            {
                "name": provider_name,
                "capability_token": str(item.get("capability_token") or ""),
                "supported_modes": list(item.get("supported_modes") or []),
                "models": provider_models,
                "installed": True,
                "used_in_app": provider_name in ai_providers,
                "default_model": default_model,
                "secret_name": secret_name,
            }
        )

    providers.sort(key=lambda row: str(row.get("name") or ""))
    return {
        "ok": True,
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "settings_path": settings_path.as_posix(),
        "providers": providers,
        "settings": settings,
    }


def apply_providers_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    action = _text(body.get("action")) or "save"
    if action == "status":
        payload = get_providers_payload(source, app_path)
        payload["action"] = "status"
        return payload
    if action != "save":
        raise Namel3ssError(_unknown_action_message(action))

    raw_settings = body.get("settings")
    if raw_settings is None:
        raw_settings = body.get("providers")
    if not isinstance(raw_settings, dict):
        raise Namel3ssError(_invalid_settings_message())

    normalized = _normalize_settings(raw_settings)
    settings_path = _settings_path(app_file)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    _write_settings(settings_path, normalized)

    payload = get_providers_payload(source, app_path)
    payload["action"] = "save"
    payload["settings_path"] = settings_path.as_posix()
    return payload


def _settings_path(app_file: Path) -> Path:
    return app_file.parent / SETTINGS_DIR / SETTINGS_FILENAME


def _load_settings(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{path.as_posix()} is not valid JSON.",
                why="Provider settings must be a valid JSON object.",
                fix="Fix the JSON or delete the file and save settings again from Studio.",
                example=f"rm {path.as_posix()}",
            )
        ) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_settings_file_message(path))
    raw = payload.get("providers")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise Namel3ssError(_invalid_settings_file_message(path))
    return _normalize_settings(raw)


def _write_settings(path: Path, settings: dict[str, dict[str, str]]) -> None:
    payload = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "providers": settings,
    }
    text = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def _normalize_settings(value: dict[object, object]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for raw_provider in sorted(value.keys(), key=lambda item: str(item)):
        provider_name = _text(raw_provider).lower()
        if not provider_name:
            continue
        metadata = get_provider_metadata(provider_name)
        if metadata is None:
            raise Namel3ssError(_unknown_provider_message(provider_name))
        entry = value.get(raw_provider)
        if not isinstance(entry, dict):
            raise Namel3ssError(_invalid_provider_row_message(provider_name))
        default_model = _text(entry.get("default_model"))
        if default_model:
            validate_model_identifier(model_identifier=default_model, provider_name=provider_name)
        secret_name = _normalize_secret_reference(entry.get("secret_name"))
        row: dict[str, str] = {}
        if default_model:
            row["default_model"] = default_model
        if secret_name:
            row["secret_name"] = secret_name
        output[provider_name] = row
    return output


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _normalize_secret_reference(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    if any(not (ch.isalnum() or ch in {"_", "-"}) for ch in text):
        raise Namel3ssError(
            build_guidance_message(
                what="Secret name contains invalid characters.",
                why="Provider secret names may only contain letters, numbers, underscores, and hyphens.",
                fix="Use a stable key-style name.",
                example="NAMEL3SS_HUGGINGFACE_API_KEY",
            )
        )
    return text


def _unknown_action_message(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown providers action '{action}'.",
        why="Supported provider actions are status and save.",
        fix="Use action 'status' to fetch settings or 'save' to persist settings.",
        example='{"action":"save","settings":{"huggingface":{"default_model":"huggingface:bert-base-uncased","secret_name":"NAMEL3SS_HUGGINGFACE_API_KEY"}}}',
    )


def _invalid_settings_message() -> str:
    return build_guidance_message(
        what="Provider settings payload is invalid.",
        why="The API expects a settings object keyed by provider name.",
        fix="Submit a JSON object in settings.",
        example='{"action":"save","settings":{"speech":{"default_model":"speech:whisper-base","secret_name":"NAMEL3SS_SPEECH_API_KEY"}}}',
    )


def _invalid_settings_file_message(path: Path) -> str:
    return build_guidance_message(
        what=f"{path.as_posix()} has an invalid format.",
        why="Provider settings must contain a top-level providers object.",
        fix="Replace the file with a valid object or save again from Studio.",
        example='{"schema_version":1,"providers":{"vision_gen":{"default_model":"vision_gen:stable-diffusion"}}}',
    )


def _unknown_provider_message(provider_name: str) -> str:
    return build_guidance_message(
        what=f"Unknown provider '{provider_name}' in provider settings.",
        why="Only registered provider packs can be configured.",
        fix="Use one of the provider pack names returned by /api/providers.",
        example="huggingface",
    )


def _invalid_provider_row_message(provider_name: str) -> str:
    return build_guidance_message(
        what=f"Provider settings row for '{provider_name}' is invalid.",
        why="Each provider row must be an object with default_model and/or secret_name.",
        fix="Send an object for each provider.",
        example='{"default_model":"huggingface:bert-base-uncased","secret_name":"NAMEL3SS_HUGGINGFACE_API_KEY"}',
    )


__all__ = ["apply_providers_payload", "get_providers_payload"]
