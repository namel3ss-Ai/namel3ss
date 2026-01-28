from __future__ import annotations

from pathlib import Path

from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest


TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "namel3ss" / "templates"
TEMPLATE_APPS = [
    TEMPLATES_DIR / "operations_dashboard" / "app.ai",
    TEMPLATES_DIR / "onboarding" / "app.ai",
    TEMPLATES_DIR / "composition" / "app.ai",
    TEMPLATES_DIR / "support_inbox" / "app.ai",
]


def _load_program(path: Path):
    source = path.read_text(encoding="utf-8")
    ast_program = parse(source)
    ir_program = lower_program(ast_program)
    return ir_program


def _manifest(ir_program, state=None, store=None):
    return build_manifest(ir_program, state=state or {}, store=store or MemoryStore())


def _walk_elements(elements):
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)


def test_templates_parse_and_manifest():
    for app_path in TEMPLATE_APPS:
        ir_program = _load_program(app_path)
        manifest = _manifest(ir_program)
        assert manifest["pages"]
        assert manifest["actions"]


def test_templates_include_tables_or_lists():
    for app_path in TEMPLATE_APPS:
        ir_program = _load_program(app_path)
        manifest = _manifest(ir_program)
        element_types = {
            element.get("type")
            for page in manifest["pages"]
            for element in _walk_elements(page.get("elements") or [])
        }
        assert element_types.intersection({"table", "list"})


def test_templates_include_compose():
    for app_path in TEMPLATE_APPS:
        ir_program = _load_program(app_path)
        manifest = _manifest(ir_program)
        element_types = {
            element.get("type")
            for page in manifest["pages"]
            for element in _walk_elements(page.get("elements") or [])
        }
        assert "compose" in element_types


def test_operations_dashboard_flow_action():
    ir_program = _load_program(TEMPLATES_DIR / "operations_dashboard" / "app.ai")
    store = MemoryStore()
    state = {}
    manifest = _manifest(ir_program, state=state, store=store)
    call_flow_actions = [
        aid
        for aid, action in manifest["actions"].items()
        if action.get("type") == "call_flow"
    ]
    assert call_flow_actions
    ok = handle_action(
        ir_program,
        action_id=call_flow_actions[0],
        payload={},
        state=state,
        store=store,
    )
    assert ok["ok"] is True
