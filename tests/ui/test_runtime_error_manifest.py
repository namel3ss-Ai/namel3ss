from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.runtime_error import inject_runtime_error_elements
from tests.conftest import lower_ir_program


def _runtime_error(category: str, stable_code: str) -> dict[str, str]:
    return {
        "category": category,
        "message": f"{category} message",
        "hint": f"{category} hint",
        "origin": "runtime",
        "stable_code": stable_code,
    }


def test_runtime_error_manifest_injection_for_standard_page() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    runtime_errors = [
        _runtime_error("policy_denied", "runtime.policy_denied"),
        _runtime_error("provider_mock_active", "runtime.provider_mock_active.openai"),
    ]
    inject_runtime_error_elements(manifest, runtime_errors)

    elements = manifest["pages"][0]["elements"]
    assert elements[0]["type"] == "runtime_error"
    assert elements[0]["category"] == "policy_denied"
    assert elements[0]["stable_code"] == "runtime.policy_denied"
    assert elements[0]["diagnostics"] == [runtime_errors[1]]


def test_runtime_error_manifest_injection_for_layout_page() -> None:
    source = '''
spec is "1.0"

page "dashboard":
  layout:
    header:
      text is "Header"
    main:
      text is "Main"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    runtime_errors = [_runtime_error("runtime_internal", "runtime.runtime_internal")]
    inject_runtime_error_elements(manifest, runtime_errors)

    main = manifest["pages"][0]["layout"]["main"]
    assert main[0]["type"] == "runtime_error"
    assert main[0]["category"] == "runtime_internal"


def test_runtime_error_manifest_injection_is_idempotent() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    runtime_errors = [_runtime_error("action_denied", "runtime.action_denied")]
    inject_runtime_error_elements(manifest, runtime_errors)
    inject_runtime_error_elements(manifest, runtime_errors)

    elements = manifest["pages"][0]["elements"]
    assert [entry.get("type") for entry in elements].count("runtime_error") == 1
