from pathlib import Path

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _manifest_for(path: Path):
    source = path.read_text(encoding="utf-8")
    program = lower_ir_program(source)
    return build_manifest(program, state={}, store=None)


def _walk_elements(nodes):
    for el in nodes or []:
        yield el
        for child in el.get("children", []) or []:
            yield from _walk_elements(child if isinstance(child, list) else [child])


def test_crud_dashboard_manifest_actions():
    mf = _manifest_for(Path("examples/demo_crud_dashboard.ai"))
    assert mf["pages"]
    assert any(el["type"] == "table" for el in _walk_elements(mf["pages"][0]["elements"]))
    assert any(action.get("type") == "call_flow" for action in mf["actions"].values())


def test_onboarding_manifest():
    mf = _manifest_for(Path("examples/demo_onboarding_flow.ai"))
    assert mf["pages"][0]["elements"]
    assert any(el["type"] == "form" for el in _walk_elements(mf["pages"][0]["elements"]))


def test_ai_assistant_manifest_actions():
    mf = _manifest_for(Path("examples/demo_ai_assistant_over_records.ai"))
    assert mf["pages"]
    assert any(action.get("type") == "call_flow" for action in mf["actions"].values())
