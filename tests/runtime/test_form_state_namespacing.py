from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''record "inventory.Product":
  name text

page "home": requires true
  form is "inventory.Product"
'''


def test_form_submission_namespaces_state_for_qualified_record():
    program = lower_ir_program(SOURCE)
    store = MemoryStore()
    manifest = build_manifest(program, state={}, store=store)
    actions = manifest.get("actions", {})
    action_id = next(aid for aid, entry in actions.items() if entry.get("type") == "submit_form")
    response = handle_action(program, action_id=action_id, payload={"values": {"name": "Widget"}}, store=store)
    assert response["ok"] is True
    assert response["state"]["inventory"]["product"]["name"] == "Widget"
