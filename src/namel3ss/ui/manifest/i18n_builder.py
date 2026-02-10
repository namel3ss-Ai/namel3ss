from __future__ import annotations

from typing import Mapping

from namel3ss.i18n.rtl_utils import locale_direction

_DEFAULT_LOCALE = "en"


def build_i18n_manifest(
    program: object,
    *,
    capabilities: tuple[str, ...],
    state: Mapping[str, object] | None,
    studio_mode: bool,
) -> dict[str, object]:
    config = _program_i18n_config(program)
    configured_locale = str(config.get("locale") or _DEFAULT_LOCALE)
    fallback_locale = str(config.get("fallback_locale") or configured_locale or _DEFAULT_LOCALE)
    translations = _sorted_mapping(config.get("translations"))
    available_locales = _normalize_locales(config.get("locales"), configured_locale, fallback_locale, translations)

    enabled = "ui.i18n" in {str(item).strip().lower() for item in capabilities} or studio_mode
    runtime_locale = _state_locale(state)
    selected_locale = configured_locale
    warnings: list[str] = []

    if enabled and runtime_locale:
        selected_locale = runtime_locale
    if selected_locale not in available_locales:
        if selected_locale != configured_locale:
            warnings.append(f"Locale '{selected_locale}' is unavailable; using '{configured_locale}'.")
        selected_locale = configured_locale
    if selected_locale not in available_locales:
        selected_locale = fallback_locale if fallback_locale in available_locales else _DEFAULT_LOCALE

    if not enabled and config:
        warnings.append("Missing capability ui.i18n; using default locale behavior.")

    payload: dict[str, object] = {
        "enabled": enabled,
        "locale": selected_locale,
        "fallback_locale": fallback_locale,
        "available_locales": available_locales,
        "direction": locale_direction(selected_locale),
        "rtl": locale_direction(selected_locale) == "rtl",
    }
    if translations:
        payload["translations"] = translations
    if warnings:
        payload["warnings"] = sorted(warnings)
    return payload


def _program_i18n_config(program: object) -> dict[str, object]:
    raw = getattr(program, "i18n_config", None)
    if isinstance(raw, Mapping):
        keyed = sorted(((str(key), key) for key in raw.keys()), key=lambda item: item[0])
        return {key_text: raw[original_key] for key_text, original_key in keyed}
    return {}


def _normalize_locales(
    raw_locales: object,
    configured_locale: str,
    fallback_locale: str,
    translations: Mapping[str, object],
) -> list[str]:
    candidates: list[str] = []
    if isinstance(raw_locales, list):
        for item in raw_locales:
            if isinstance(item, str) and item.strip():
                candidates.append(item.strip())
    candidates.append(configured_locale)
    candidates.append(fallback_locale)
    for key in sorted(translations.keys()):
        candidates.append(str(key))

    deduped: list[str] = []
    seen: set[str] = set()
    for locale in candidates:
        value = str(locale).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    if not deduped:
        return [_DEFAULT_LOCALE]
    return deduped


def _state_locale(state: Mapping[str, object] | None) -> str | None:
    if not isinstance(state, Mapping):
        return None
    ui = state.get("ui")
    if not isinstance(ui, Mapping):
        return None
    locale = ui.get("locale")
    if not isinstance(locale, str):
        return None
    value = locale.strip()
    return value or None


def _sorted_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    keyed = sorted(((str(key), key) for key in value.keys()), key=lambda item: item[0])
    return {key_text: value[original_key] for key_text, original_key in keyed}


__all__ = ["build_i18n_manifest"]
