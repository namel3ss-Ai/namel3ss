from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.ui.explain.build_core import build_ui_explain_pack
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


FIXTURE_APP = Path("tests/fixtures/ui_patterns_app.ai")
MANIFEST_GOLDEN = Path("tests/fixtures/ui_patterns_manifest_golden.json")
EXPLAIN_GOLDEN = Path("tests/fixtures/ui_patterns_explain_golden.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ui_pattern_manifest_matches_golden():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={}, store=None)
    expected = _load_json(MANIFEST_GOLDEN)
    assert manifest == expected


def test_ui_pattern_explain_matches_golden():
    root = Path(__file__).resolve().parents[2]
    app_path = root / FIXTURE_APP
    pack = build_ui_explain_pack(root, str(app_path))
    expected = _load_json(EXPLAIN_GOLDEN)
    assert pack == expected
