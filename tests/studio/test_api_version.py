from namel3ss.studio.api import get_version_payload


def test_api_version_payload():
    payload = get_version_payload()
    assert payload["ok"] is True
    assert isinstance(payload.get("version"), str)
    assert payload["version"]
