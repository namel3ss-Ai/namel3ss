from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.composition.explain import (
    MAX_CALLS,
    build_composition_explain_pack,
)

BASE_FIXTURE = Path("tests/fixtures/composition_explain_run_payload.json")
EXPECTED_FIXTURE = Path("tests/fixtures/composition_explain_expected.json")
REDACTION_FIXTURE = Path("tests/fixtures/composition_explain_redaction.json")
TRUNCATION_FIXTURE = Path("tests/fixtures/composition_explain_truncation.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_composition_explain_matches_fixture() -> None:
    run_payload = _load_json(BASE_FIXTURE)
    expected = _load_json(EXPECTED_FIXTURE)
    pack = build_composition_explain_pack(run_payload)
    assert pack == expected


def test_composition_explain_redacts_paths_and_secrets(tmp_path: Path) -> None:
    run_payload = _load_json(REDACTION_FIXTURE)
    pack = build_composition_explain_pack(
        run_payload,
        project_root=tmp_path,
        app_path=tmp_path / "app.ai",
        secret_values=["TOPSECRET"],
    )
    text = json.dumps(pack, sort_keys=True)
    assert "TOPSECRET" not in text
    assert "/Users/alice/project/app.ai" not in text
    assert "/Users/alice" not in text


def test_composition_explain_truncates_calls() -> None:
    run_payload = _load_json(TRUNCATION_FIXTURE)
    pack = build_composition_explain_pack(run_payload)
    call_tree = pack.get("call_tree") or {}
    calls = call_tree.get("calls") or []
    assert call_tree.get("total") > MAX_CALLS
    assert call_tree.get("truncated") is True
    assert len(calls) == MAX_CALLS
