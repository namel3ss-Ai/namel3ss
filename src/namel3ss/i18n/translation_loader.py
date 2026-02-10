from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from namel3ss.errors.base import Namel3ssError

from .rtl_utils import apply_rtl_to_manifest, locale_direction


_VISIBLE_STRING_KEYS: tuple[str, ...] = (
    "title",
    "subtitle",
    "label",
    "text",
    "placeholder",
    "description",
    "empty",
    "hint",
    "name",
    "content",
)

_VALUE_ALIASES: tuple[str, ...] = (
    "title",
    "text",
)


@dataclass(frozen=True)
class TranslationBundle:
    locale: str
    fallback_locale: str
    messages: dict[str, str]


def load_translation_bundle(source: Path | Mapping[str, object], *, locale: str | None = None) -> TranslationBundle:
    if isinstance(source, Path):
        payload = _read_bundle_file(source)
    elif isinstance(source, Mapping):
        payload = dict(source)
    else:
        raise Namel3ssError("Translation source must be a path or mapping.")

    resolved_locale = str(locale or payload.get("locale") or payload.get("source_locale") or "en")
    fallback_locale = str(payload.get("fallback_locale") or payload.get("source_locale") or "en")
    raw_messages = payload.get("messages", {})
    if not isinstance(raw_messages, Mapping):
        raise Namel3ssError("Translation bundle messages must be a mapping.")
    messages: dict[str, str] = {}
    for key in sorted(str(item) for item in raw_messages.keys()):
        original_key = _resolve_original_key(raw_messages, key)
        if original_key is None:
            continue
        value = raw_messages[original_key]
        text = _pick_message_text(value, locale=resolved_locale, fallback_locale=fallback_locale)
        if text is None:
            continue
        messages[key] = text
    return TranslationBundle(locale=resolved_locale, fallback_locale=fallback_locale, messages=messages)


def apply_translations_to_manifest(
    manifest: Mapping[str, object],
    *,
    bundle: TranslationBundle,
    fallback_bundle: TranslationBundle | None = None,
) -> dict[str, object]:
    localized, _ = _walk_and_translate(
        value=dict(manifest),
        path=("manifest",),
        bundle=bundle,
        fallback_bundle=fallback_bundle,
    )
    if not isinstance(localized, dict):
        return dict(manifest)
    return localized


def localize_manifest(
    manifest: Mapping[str, object],
    *,
    bundle: TranslationBundle,
    fallback_bundle: TranslationBundle | None = None,
) -> dict[str, object]:
    translated = apply_translations_to_manifest(manifest, bundle=bundle, fallback_bundle=fallback_bundle)
    return apply_rtl_to_manifest(translated, locale=bundle.locale)


def _walk_and_translate(
    *,
    value: object,
    path: tuple[str, ...],
    bundle: TranslationBundle,
    fallback_bundle: TranslationBundle | None,
) -> tuple[object, list[str]]:
    if isinstance(value, dict):
        translated: dict[str, object] = {}
        warnings: list[str] = []
        value_alias = _value_alias_for_mapping(value)
        for key in sorted(str(item) for item in value.keys()):
            original_key = _resolve_original_key(value, key)
            if original_key is None:
                continue
            item = value[original_key]
            next_path = (*path, key)
            if key in _VISIBLE_STRING_KEYS and isinstance(item, str):
                message_key = _message_key(next_path)
                translated_value = _resolve_translation(
                    message_key,
                    default=item,
                    bundle=bundle,
                    fallback_bundle=fallback_bundle,
                )
                translated[key] = translated_value
                if translated_value == item and message_key not in bundle.messages:
                    warnings.append(message_key)
                continue
            if key == "value" and value_alias and isinstance(item, str):
                aliased_message_key = _message_key((*path, value_alias))
                raw_message_key = _message_key(next_path)
                translated_value, used_key = _resolve_translation_for_candidates(
                    (aliased_message_key, raw_message_key),
                    default=item,
                    bundle=bundle,
                    fallback_bundle=fallback_bundle,
                )
                translated[key] = translated_value
                if translated_value == item and used_key is None:
                    warnings.append(aliased_message_key)
                continue
            nested, nested_warnings = _walk_and_translate(
                value=item,
                path=next_path,
                bundle=bundle,
                fallback_bundle=fallback_bundle,
            )
            translated[key] = nested
            warnings.extend(nested_warnings)
        if path == ("manifest",):
            i18n_payload = dict(translated.get("i18n") or {})
            i18n_payload["locale"] = bundle.locale
            i18n_payload["fallback_locale"] = bundle.fallback_locale
            i18n_payload["direction"] = locale_direction(bundle.locale)
            if warnings:
                i18n_payload["missing_keys"] = sorted(set(warnings))
            translated["i18n"] = i18n_payload
        return translated, warnings

    if isinstance(value, list):
        translated_items: list[object] = []
        warnings: list[str] = []
        for index, item in enumerate(value):
            nested, nested_warnings = _walk_and_translate(
                value=item,
                path=(*path, str(index)),
                bundle=bundle,
                fallback_bundle=fallback_bundle,
            )
            translated_items.append(nested)
            warnings.extend(nested_warnings)
        return translated_items, warnings

    return value, []


def _resolve_translation(
    key: str,
    *,
    default: str,
    bundle: TranslationBundle,
    fallback_bundle: TranslationBundle | None,
) -> str:
    if key in bundle.messages:
        return bundle.messages[key]
    if fallback_bundle and key in fallback_bundle.messages:
        return fallback_bundle.messages[key]
    return default


def _resolve_translation_for_candidates(
    keys: tuple[str, ...],
    *,
    default: str,
    bundle: TranslationBundle,
    fallback_bundle: TranslationBundle | None,
) -> tuple[str, str | None]:
    for key in keys:
        if key in bundle.messages:
            return bundle.messages[key], key
    if fallback_bundle is not None:
        for key in keys:
            if key in fallback_bundle.messages:
                return fallback_bundle.messages[key], key
    return default, None


def _message_key(path: tuple[str, ...]) -> str:
    return ".".join(path[1:])


def _pick_message_text(value: object, *, locale: str, fallback_locale: str) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        return None
    localized = value.get(locale)
    if isinstance(localized, str):
        return localized
    fallback = value.get(fallback_locale)
    if isinstance(fallback, str):
        return fallback
    source = value.get("en")
    if isinstance(source, str):
        return source
    return None


def _read_bundle_file(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            f"Invalid translation JSON at {path.as_posix()}: {err.msg}",
            line=err.lineno,
            column=err.colno,
        ) from err
    if not isinstance(payload, dict):
        raise Namel3ssError("Translation bundle root must be an object.")
    return payload


def _resolve_original_key(mapping: Mapping[str, object], key_text: str) -> str | None:
    for key in mapping.keys():
        if str(key) == key_text:
            return key
    return None


def _value_alias_for_mapping(mapping: Mapping[str, object]) -> str | None:
    type_key = _resolve_original_key(mapping, "type")
    if type_key is None:
        return None
    value = mapping[type_key]
    if not isinstance(value, str):
        return None
    element_type = value.strip().lower()
    if element_type in _VALUE_ALIASES:
        return element_type
    return None


__all__ = [
    "TranslationBundle",
    "apply_translations_to_manifest",
    "load_translation_bundle",
    "localize_manifest",
]
