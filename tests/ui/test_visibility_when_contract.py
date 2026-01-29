from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.explain.build_core import build_ui_explain_pack
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


FIXTURE_APP = Path("tests/fixtures/ui_visibility_when_app.ai")
MANIFEST_TRUE = Path("tests/fixtures/ui_visibility_when_manifest_true.json")
MANIFEST_FALSE = Path("tests/fixtures/ui_visibility_when_manifest_false.json")
EXPLAIN_GOLDEN = Path("tests/fixtures/ui_visibility_when_explain_golden.json")
INVALID_FIXTURE = Path("tests/fixtures/ui_visibility_when_invalid.ai")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_visibility_when_manifest_true():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={"ready": True}, store=None)
    expected = _load_json(MANIFEST_TRUE)
    assert manifest == expected


def test_visibility_when_manifest_false():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={"ready": False}, store=None)
    expected = _load_json(MANIFEST_FALSE)
    assert manifest == expected


def test_visibility_when_explain_matches_golden():
    root = Path(__file__).resolve().parents[2]
    app_path = root / FIXTURE_APP
    pack = build_ui_explain_pack(root, str(app_path))
    expected = _load_json(EXPLAIN_GOLDEN)
    assert pack == expected


def test_visibility_when_invalid_state_path():
    source = INVALID_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Visibility requires state.<path>." in str(exc.value)
