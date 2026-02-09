from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.audit_viewer import inject_audit_viewer_elements
from tests.conftest import lower_ir_program


def _run_artifact() -> dict:
    return {
        "schema_version": "run_artifact@1",
        "run_id": "a" * 64,
        "retrieval_trace": [{"chunk_id": "doc-1:0", "rank": 1, "reason": "semantic_match"}],
        "runtime_errors": [],
        "checksums": {"output_hash": "b" * 64},
    }


def test_audit_viewer_manifest_injection_for_standard_page() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    inject_audit_viewer_elements(
        manifest,
        run_artifact=_run_artifact(),
        audit_bundle={
            "schema_version": "audit_bundle@1",
            "run_id": "a" * 64,
            "integrity_hash": "c" * 64,
            "run_artifact_path": "audit/a/run_artifact.json",
            "bundle_path": "audit/a/bundle.json",
        },
        audit_policy_status={"mode": "optional", "required": False, "forbidden": False, "attempted": True, "written": True},
    )
    elements = manifest["pages"][0]["elements"]
    assert elements[0]["type"] == "audit_viewer"
    assert elements[0]["run_id"] == "a" * 64
    assert elements[0]["retrieval_count"] == 1


def test_audit_viewer_manifest_injection_is_idempotent() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    args = {
        "run_artifact": _run_artifact(),
        "audit_bundle": {},
        "audit_policy_status": {"mode": "optional", "required": False, "forbidden": False, "attempted": False, "written": False},
    }
    inject_audit_viewer_elements(manifest, **args)
    inject_audit_viewer_elements(manifest, **args)
    elements = manifest["pages"][0]["elements"]
    assert [entry.get("type") for entry in elements].count("audit_viewer") == 1
