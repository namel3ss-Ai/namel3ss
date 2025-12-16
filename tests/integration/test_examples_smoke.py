from __future__ import annotations

from pathlib import Path

from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest


EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


def _load_program(path: Path):
    source = path.read_text(encoding="utf-8")
    ast_program = parse(source)
    ir_program = lower_program(ast_program)
    return source, ir_program


def _manifest(ir_program, state=None, store=None):
    return build_manifest(ir_program, state=state or {}, store=store or MemoryStore())


def test_examples_parse_and_manifest():
    for name in ["demo_crud_dashboard.ai", "demo_ai_assistant_over_records.ai", "demo_multi_agent_workflow.ai"]:
        source, ir_program = _load_program(EXAMPLES_DIR / name)
        manifest = _manifest(ir_program)
        assert manifest["pages"]
        assert manifest["actions"]


def test_crud_demo_actions():
    source, ir_program = _load_program(EXAMPLES_DIR / "demo_crud_dashboard.ai")
    store = MemoryStore()
    state = {}
    ok = handle_action(
        ir_program,
        action_id="page.home.form.customer",
        payload={"values": {"name": "Test", "email": "test@example.com", "age": 25}},
        state=state,
        store=store,
    )
    assert ok["ok"] is True
    bad = handle_action(
        ir_program,
        action_id="page.home.form.customer",
        payload={"values": {"email": "bad"}},
        state=state,
        store=store,
    )
    assert bad["ok"] is False
    assert bad["errors"]


def test_ai_assistant_demo():
    source, ir_program = _load_program(EXAMPLES_DIR / "demo_ai_assistant_over_records.ai")
    state = {}
    store = MemoryStore()
    resp = handle_action(ir_program, action_id="page.notes.button.ask_assistant", payload={}, state=state, store=store)
    assert resp["ok"] is True
    assert resp["traces"]
    assert "reply" in resp["state"]


def test_multi_agent_demo():
    source, ir_program = _load_program(EXAMPLES_DIR / "demo_multi_agent_workflow.ai")
    state = {}
    store = MemoryStore()
    resp = handle_action(ir_program, action_id="page.workflow.button.run_workflow", payload={}, state=state, store=store)
    assert resp["ok"] is True
    assert any(tr.get("type") == "parallel_agents" for tr in resp["traces"])
    assert "plan" in resp["state"]
    assert "final" in resp["state"]
