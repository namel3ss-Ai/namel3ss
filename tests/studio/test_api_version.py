from namel3ss.studio.api import get_version_payload
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION


def test_api_version_payload():
    payload = get_version_payload()
    assert payload["ok"] is True
    assert isinstance(payload.get("version"), str)
    assert payload["version"]
    assert payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
