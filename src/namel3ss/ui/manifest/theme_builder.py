from __future__ import annotations

from typing import Mapping

from namel3ss.runtime.theme_state import merge_theme_tokens
from namel3ss.ui.theme.theme_config import serialize_theme_config, theme_config_from_program
from namel3ss.ui.theme.theme_loader import load_theme_bundle_from_program
from namel3ss.ui.theme.theme_token_validation import build_theme_token_contract
from namel3ss.ui.theme.theme_tokens import base_theme_names, token_schema
from namel3ss.ui.theme_tokens import UI_THEME_TOKEN_ORDER


def build_theme_manifest(
    program: object,
    *,
    ui_schema_version: str,
    theme_setting: str,
    theme_current: str,
    persisted_theme_normalized: str | None,
    effective_value: str,
    source_value: str,
    ui_theme_enabled: bool,
    runtime_theme_settings: Mapping[str, str] | None,
) -> dict[str, object]:
    theme_definition = _resolved_theme_definition(program)
    has_theme_definition = _has_theme_definition(theme_definition)

    theme_preference = dict(getattr(program, "theme_preference", {"allow_override": False, "persist": "none"}) or {})
    if has_theme_definition:
        theme_preference.setdefault("storage_key", "namel3ss_theme")

    legacy_theme_tokens = _ordered_dict(getattr(program, "theme_tokens", {}) or {})

    raw_theme_config = getattr(program, "ui_theme_config", None)
    if isinstance(raw_theme_config, Mapping):
        bundle = load_theme_bundle_from_program(program)
        visual_theme_name = bundle.base_theme
        visual_theme_tokens = _ordered_dict(bundle.tokens)
        visual_theme_css = bundle.css
        visual_theme_css_hash = bundle.css_hash
        visual_theme_font_url = bundle.font_url
        theme_config_payload = dict(bundle.config)
    else:
        visual_theme_name = str(getattr(program, "ui_visual_theme_name", "default") or "default")
        visual_theme_tokens = _ordered_dict(getattr(program, "ui_visual_theme_tokens", {}) or {})
        visual_theme_css = str(getattr(program, "ui_visual_theme_css", "") or "")
        visual_theme_css_hash = str(getattr(program, "ui_visual_theme_css_hash", "") or "")
        visual_theme_font_url = getattr(program, "ui_visual_theme_font_url", None)
        theme_config_payload = serialize_theme_config(theme_config_from_program(program))

    merged_theme_tokens = _ordered_dict({**legacy_theme_tokens, **visual_theme_tokens})

    payload: dict[str, object] = {
        "schema_version": ui_schema_version,
        "setting": theme_setting,
        "current": theme_current,
        "persisted_current": persisted_theme_normalized,
        "effective": effective_value,
        "source": source_value,
        "runtime_supported": bool(getattr(program, "theme_runtime_supported", False)),
        "theme_name": visual_theme_name,
        "base_theme": str(theme_config_payload.get("base_theme") or "default"),
        "themes_available": list(base_theme_names()),
        "tokens": merged_theme_tokens,
        "runtime_tokens": legacy_theme_tokens,
        "css": visual_theme_css,
        "css_hash": visual_theme_css_hash,
        "preference": theme_preference,
        "config": {
            "base_theme": str(theme_config_payload.get("base_theme") or "default"),
            "overrides": _ordered_dict(theme_config_payload.get("overrides") or {}),
        },
        "token_schema": token_schema(),
    }

    if ui_theme_enabled:
        payload["tokens_v2"] = build_theme_token_contract(merged_theme_tokens, mode=theme_current)
        runtime_tokens = merge_theme_tokens(dict(runtime_theme_settings or {}))
        for key in UI_THEME_TOKEN_ORDER:
            payload[key] = runtime_tokens.get(key)

    if isinstance(visual_theme_font_url, str) and visual_theme_font_url:
        payload["font_url"] = visual_theme_font_url

    responsive_theme_tokens = getattr(program, "responsive_theme_tokens", {}) or {}
    if isinstance(responsive_theme_tokens, Mapping) and responsive_theme_tokens:
        keyed = sorted(((str(key), key) for key in responsive_theme_tokens.keys()), key=lambda item: item[0])
        payload["responsive_tokens"] = {
            key_text: list(responsive_theme_tokens[original_key])
            for key_text, original_key in keyed
        }

    if has_theme_definition:
        payload["definition"] = _serialize_theme_definition(theme_definition)

    return payload


def _resolved_theme_definition(program: object) -> object | None:
    resolved_theme = getattr(program, "resolved_theme", None)
    return getattr(resolved_theme, "definition", None)


def _has_theme_definition(theme_definition: object | None) -> bool:
    if theme_definition is None:
        return False
    return bool(
        getattr(theme_definition, "preset", None)
        or getattr(theme_definition, "brand_palette", None)
        or getattr(theme_definition, "tokens", None)
        or getattr(theme_definition, "responsive_tokens", None)
        or getattr(theme_definition, "harmonize", None)
        or getattr(theme_definition, "allow_low_contrast", None)
        or getattr(theme_definition, "density", None)
        or getattr(theme_definition, "motion", None)
        or getattr(theme_definition, "shape", None)
        or getattr(theme_definition, "surface", None)
    )


def _serialize_theme_definition(theme_definition: object) -> dict[str, object]:
    responsive_tokens = getattr(theme_definition, "responsive_tokens", None) or {}
    keyed = sorted(((str(key), key) for key in responsive_tokens.keys()), key=lambda item: item[0])
    responsive_payload = {
        key_text: list(responsive_tokens[original_key])
        for key_text, original_key in keyed
    }
    return {
        "preset": getattr(theme_definition, "preset", None),
        "brand_palette": _ordered_dict(getattr(theme_definition, "brand_palette", None) or {}),
        "tokens": _ordered_dict(getattr(theme_definition, "tokens", None) or {}),
        "responsive_tokens": responsive_payload,
        "harmonize": bool(getattr(theme_definition, "harmonize", False)),
        "allow_low_contrast": bool(getattr(theme_definition, "allow_low_contrast", False)),
        "axes": {
            "density": getattr(theme_definition, "density", None),
            "motion": getattr(theme_definition, "motion", None),
            "shape": getattr(theme_definition, "shape", None),
            "surface": getattr(theme_definition, "surface", None),
        },
    }


def _ordered_dict(values: Mapping[str, object] | dict[str, object]) -> dict[str, object]:
    mapping = values if isinstance(values, Mapping) else {}
    keyed = sorted(((str(key), key) for key in mapping.keys()), key=lambda item: item[0])
    return {key_text: mapping[original_key] for key_text, original_key in keyed}


__all__ = ["build_theme_manifest"]
