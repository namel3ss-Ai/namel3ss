from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION
from namel3ss.spec_versions import load_spec_versions


EXPECTED_SPEC_VERSIONS = {
    "language_core": 1,
    "tool_dsl": 1,
    "tool_protocol": 1,
    "pack_manifest": 1,
    "bindings_schema": 1,
    "runner_contract": 1,
    "ui_manifest": 1,
    "identity_schema": 1,
    "persistence_contract": 1,
    "trace_schema": 1,
}


def test_spec_versions_are_frozen() -> None:
    assert load_spec_versions() == EXPECTED_SPEC_VERSIONS


def test_tool_protocol_version_matches_runtime() -> None:
    versions = load_spec_versions()
    assert versions["tool_protocol"] == PROTOCOL_VERSION
