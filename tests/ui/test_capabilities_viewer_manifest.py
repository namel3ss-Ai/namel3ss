from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.capabilities_viewer import inject_capabilities_viewer_elements
from tests.conftest import lower_ir_program


def _packs() -> list[dict[str, object]]:
    return [
        {
            "name": "http_client",
            "version": "1.0.0",
            "provided_actions": ["http.get", "http.post"],
            "required_permissions": ["http"],
            "runtime_bindings": {"executor": "namel3ss.runtime.capabilities.http_client"},
            "effect_capabilities": ["network"],
            "contract_version": "runtime-ui@1",
            "purity": "effectful",
            "replay_mode": "verify",
        }
    ]


def test_capabilities_manifest_injection_is_idempotent() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    inject_capabilities_viewer_elements(
        manifest,
        capabilities_enabled=_packs(),
        capability_versions={"http_client": "1.0.0"},
    )
    inject_capabilities_viewer_elements(
        manifest,
        capabilities_enabled=_packs(),
        capability_versions={"http_client": "1.0.0"},
    )
    elements = manifest["pages"][0]["elements"]
    assert [entry.get("type") for entry in elements].count("capabilities") == 1
    assert elements[0]["type"] == "capabilities"
