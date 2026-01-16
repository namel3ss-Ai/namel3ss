import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.media import MediaValidationMode, validate_media_reference
from namel3ss.parser.core import parse
from namel3ss.runtime.dev_overlay import build_dev_overlay_payload
from namel3ss.ui.settings import validate_ui_value


FIXTURE_DIR = Path("tests/fixtures")


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_dev_overlay_parse_error_snapshot():
    source = 'spec is "1.0"\n\npage "home":\n  text is\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    payload = build_error_from_exception(excinfo.value, kind="parse", source=source)
    overlay = build_dev_overlay_payload(payload)
    assert overlay == _load_fixture("dev_overlay_parse.json")


def test_dev_overlay_validation_error_snapshot():
    with pytest.raises(Namel3ssError) as excinfo:
        validate_ui_value("theme", "blorple", line=1, column=1)
    payload = build_error_from_exception(excinfo.value, kind="manifest")
    overlay = build_dev_overlay_payload(payload)
    assert overlay == _load_fixture("dev_overlay_validation.json")


def test_dev_overlay_missing_media_snapshot():
    with pytest.raises(Namel3ssError) as excinfo:
        validate_media_reference(
            "welcome",
            registry={},
            mode=MediaValidationMode.BUILD,
            line=1,
            column=1,
        )
    payload = build_error_from_exception(excinfo.value, kind="manifest")
    overlay = build_dev_overlay_payload(payload)
    assert overlay == _load_fixture("dev_overlay_missing_media.json")
