from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from namel3ss.determinism import canonical_json_dumps

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


def extract_manifest_strings(manifest: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Extract user-visible strings from a manifest using deterministic keys."""
    collected: dict[str, dict[str, object]] = {}
    _walk_manifest(manifest, path=("manifest",), out=collected)
    return {key: collected[key] for key in sorted(collected)}


def format_translation_catalog(
    strings: Mapping[str, Mapping[str, object]],
    *,
    source_locale: str = "en",
) -> dict[str, object]:
    messages: dict[str, dict[str, object]] = {}
    for key in sorted(strings):
        entry = strings[key]
        text = str(entry.get("text") or "")
        context = str(entry.get("context") or "")
        messages[key] = {
            source_locale: text,
            "context": context,
        }
    return {
        "schema_version": "1",
        "source_locale": source_locale,
        "messages": messages,
    }


def write_translation_catalog(
    strings: Mapping[str, Mapping[str, object]],
    destination: Path,
    *,
    source_locale: str = "en",
) -> Path:
    payload = format_translation_catalog(strings, source_locale=source_locale)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        canonical_json_dumps(payload, pretty=True, drop_run_keys=False) + "\n",
        encoding="utf-8",
    )
    return destination


def _walk_manifest(
    value: object,
    *,
    path: Sequence[str],
    out: dict[str, dict[str, object]],
) -> None:
    if isinstance(value, Mapping):
        value_alias = _value_alias_for_mapping(value)
        for key in sorted(str(item) for item in value.keys()):
            original_key = _resolve_original_key(value, key)
            if original_key is None:
                continue
            item = value[original_key]
            if _is_visible_key(key) and isinstance(item, str) and item.strip():
                translation_id = _translation_id(path, key)
                out[translation_id] = {
                    "text": item,
                    "context": ".".join((*path, key)),
                }
            elif key == "value" and isinstance(item, str) and item.strip() and value_alias:
                translation_id = _translation_id(path, value_alias)
                out[translation_id] = {
                    "text": item,
                    "context": ".".join((*path, key)),
                }
            _walk_manifest(item, path=(*path, key), out=out)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_manifest(item, path=(*path, str(index)), out=out)


def _translation_id(path: Sequence[str], key: str) -> str:
    # Stable identifier derived solely from deterministic manifest path.
    return ".".join((*path[1:], key))


def _is_visible_key(key: str) -> bool:
    return key in _VISIBLE_STRING_KEYS


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
    "extract_manifest_strings",
    "format_translation_catalog",
    "write_translation_catalog",
]
