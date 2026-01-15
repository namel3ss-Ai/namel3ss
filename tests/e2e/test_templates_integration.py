from __future__ import annotations

from pathlib import Path

from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest


TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "namel3ss" / "templates"
STARTER_APP = TEMPLATES_DIR / "starter" / "app.ai"
DEMO_APP = TEMPLATES_DIR / "demo" / "app.ai"


def _load_program(path: Path):
    source = path.read_text(encoding="utf-8")
    ast_program = parse(source)
    ir_program = lower_program(ast_program)
    return ir_program


def _manifest(ir_program, state=None, store=None):
    return build_manifest(ir_program, state=state or {}, store=store or MemoryStore())


def test_templates_parse_and_manifest():
    for app_path in [STARTER_APP, DEMO_APP]:
        ir_program = _load_program(app_path)
        manifest = _manifest(ir_program)
        assert manifest["pages"]
        assert manifest["actions"]


def test_starter_form_action():
    ir_program = _load_program(STARTER_APP)
    store = MemoryStore()
    state = {}
    manifest = _manifest(ir_program, state=state, store=store)
    form_actions = [
        aid
        for aid, action in manifest["actions"].items()
        if action.get("type") == "submit_form"
    ]
    assert form_actions
    ok = handle_action(
        ir_program,
        action_id=form_actions[0],
        payload={"values": {"summary": "hello", "details": "note"}},
        state=state,
        store=store,
    )
    assert ok["ok"] is True


def test_demo_ask_ai_action():
    ir_program = _load_program(DEMO_APP)
    state = {}
    store = MemoryStore()
    manifest = _manifest(ir_program, state=state, store=store)
    actions = [
        aid
        for aid, action in manifest["actions"].items()
        if action.get("type") == "call_flow" and action.get("flow") == "ask_ai"
    ]
    assert actions
    resp = handle_action(
        ir_program,
        action_id=actions[0],
        payload={"message": "hello"},
        state=state,
        store=store,
    )
    assert resp["ok"] is True
    assert resp["traces"]
