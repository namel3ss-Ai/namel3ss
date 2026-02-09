from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.state_inspector import inject_state_inspector_elements
from tests.conftest import lower_ir_program


def test_state_inspector_manifest_injection_is_deterministic() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    payload = {
        "persistence_backend": {
            "target": "file",
            "kind": "sqlite",
            "enabled": True,
            "durable": True,
            "deterministic_ordering": True,
        },
        "migration_status": {
            "schema_version": "migration_status@1",
            "state_schema_version": "state_schema@1",
            "plan_id": "plan-1",
            "last_plan_id": "plan-1",
            "applied_plan_id": "plan-1",
            "pending": False,
            "breaking": False,
            "reversible": True,
            "plan_changed": False,
            "change_count": 0,
        },
        "state_schema_version": "state_schema@1",
    }
    inject_state_inspector_elements(manifest, **payload)
    inject_state_inspector_elements(manifest, **payload)
    elements = manifest["pages"][0]["elements"]
    assert elements[0]["type"] == "state_inspector"
    assert [item["type"] for item in elements].count("state_inspector") == 1
    assert manifest["state_schema_version"] == "state_schema@1"
