from __future__ import annotations

from namel3ss.i18n.locale_formatter import format_date, format_datetime, format_number, format_time
from namel3ss.i18n.translation_loader import (
    apply_translations_to_manifest,
    load_translation_bundle,
    localize_manifest,
)


def test_translation_loader_applies_locale_and_fallback() -> None:
    manifest = {
        "pages": [
            {
                "name": "home",
                "title": "Home",
                "elements": [{"type": "text", "text": "Welcome"}],
            }
        ]
    }
    fr_bundle = load_translation_bundle(
        {
            "locale": "fr",
            "fallback_locale": "en",
            "messages": {
                "pages.0.title": {"fr": "Accueil", "en": "Home"},
            },
        }
    )
    en_bundle = load_translation_bundle(
        {
            "locale": "en",
            "fallback_locale": "en",
            "messages": {
                "pages.0.elements.0.text": {"en": "Welcome"},
            },
        }
    )

    translated = apply_translations_to_manifest(manifest, bundle=fr_bundle, fallback_bundle=en_bundle)
    assert translated["pages"][0]["title"] == "Accueil"
    assert translated["pages"][0]["elements"][0]["text"] == "Welcome"


def test_localize_manifest_sets_rtl_direction_and_layout_swap() -> None:
    manifest = {
        "pages": [
            {
                "name": "home",
                "layout": {
                    "sidebar_left": [{"type": "text", "text": "left"}],
                    "drawer_right": [{"type": "text", "text": "right"}],
                },
            }
        ]
    }
    bundle = load_translation_bundle({"locale": "ar", "fallback_locale": "en", "messages": {}})
    localized = localize_manifest(manifest, bundle=bundle)
    assert localized["i18n"]["direction"] == "rtl"
    assert localized["pages"][0]["direction"] == "rtl"
    assert localized["pages"][0]["layout"]["sidebar_left"][0]["text"] == "right"


def test_locale_formatter_outputs_are_deterministic() -> None:
    from datetime import datetime

    value = datetime(2026, 2, 10, 16, 5)
    assert format_number(12345.5, locale="en", precision=1) == "12,345.5"
    assert format_number(12345.5, locale="fr", precision=1) == "12 345,5"
    assert format_date(value, locale="en") == "2/10/2026"
    assert format_time(value, locale="en") == "4:05 PM"
    assert format_datetime(value, locale="fr") == "10/2/2026 16:05"
