from pathlib import Path

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _manifest_for(path: Path):
    source = path.read_text(encoding="utf-8")
    program = lower_ir_program(source)
    return build_manifest(program, state={}, store=None)


def test_product_dashboard_manifest_actions():
    mf = _manifest_for(Path("examples/demo_product_dashboard.ai"))
    assert mf["pages"]
    assert any(el["type"] == "table" for el in mf["pages"][0]["elements"])
    assert any(action.get("type") == "call_flow" for action in mf["actions"].values())


def test_onboarding_manifest():
    mf = _manifest_for(Path("examples/demo_onboarding_flow.ai"))
    assert mf["pages"][0]["elements"]
    assert any(el["type"] == "form" for el in mf["pages"][0]["elements"] or [])


def test_ai_assistant_manifest_actions():
    mf = _manifest_for(Path("examples/demo_ai_assistant_ui.ai"))
    assert mf["pages"]
    assert any(action.get("type") == "call_flow" for action in mf["actions"].values())
