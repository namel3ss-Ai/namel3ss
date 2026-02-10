from __future__ import annotations

from pathlib import Path

from namel3ss.i18n.i18n_extractor import (
    extract_manifest_strings,
    format_translation_catalog,
    write_translation_catalog,
)
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_extract_manifest_strings_is_deterministic() -> None:
    source = 'page "home":\n  title is "Dashboard"\n  text is "Welcome"\n'
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    first = extract_manifest_strings(manifest)
    second = extract_manifest_strings(manifest)
    assert first == second
    assert any(key.endswith("title") for key in first)


def test_format_translation_catalog_has_stable_order() -> None:
    extracted = {
        "pages.0.title": {"text": "Home", "context": "manifest.pages.0.title"},
        "pages.0.elements.0.text": {"text": "Welcome", "context": "manifest.pages.0.elements.0.text"},
    }
    payload = format_translation_catalog(extracted, source_locale="en")
    assert payload["schema_version"] == "1"
    assert list(payload["messages"].keys()) == ["pages.0.elements.0.text", "pages.0.title"]


def test_write_translation_catalog_writes_json(tmp_path: Path) -> None:
    extracted = {
        "pages.0.title": {"text": "Home", "context": "manifest.pages.0.title"},
    }
    output = write_translation_catalog(extracted, tmp_path / "translations" / "en.json")
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert '"schema_version": "1"' in text
    assert '"pages.0.title"' in text
