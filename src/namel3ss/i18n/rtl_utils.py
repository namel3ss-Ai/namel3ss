from __future__ import annotations

from copy import deepcopy
from typing import Mapping


_RTL_LANGS: set[str] = {"ar", "fa", "he", "ur"}


def is_rtl_locale(locale: str | None) -> bool:
    if not isinstance(locale, str):
        return False
    value = locale.strip().replace("_", "-").lower()
    if not value:
        return False
    language = value.split("-", 1)[0]
    return language in _RTL_LANGS


def locale_direction(locale: str | None) -> str:
    return "rtl" if is_rtl_locale(locale) else "ltr"


def apply_rtl_to_manifest(manifest: Mapping[str, object], *, locale: str | None) -> dict[str, object]:
    output = deepcopy(dict(manifest))
    direction = locale_direction(locale)
    i18n = dict(output.get("i18n") or {})
    i18n["direction"] = direction
    i18n["rtl"] = direction == "rtl"
    output["i18n"] = i18n
    if direction != "rtl":
        return output

    pages = output.get("pages")
    if not isinstance(pages, list):
        return output
    for page in pages:
        if not isinstance(page, dict):
            continue
        page["direction"] = "rtl"
        layout = page.get("layout")
        if not isinstance(layout, dict):
            continue
        left = layout.get("sidebar_left")
        right = layout.get("drawer_right")
        if isinstance(left, list) and isinstance(right, list):
            layout["sidebar_left"], layout["drawer_right"] = right, left
    return output


__all__ = ["apply_rtl_to_manifest", "is_rtl_locale", "locale_direction"]
