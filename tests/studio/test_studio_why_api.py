from pathlib import Path

from namel3ss.studio.why_api import get_why_payload


def _write_basic_app(root: Path) -> None:
    app = root / "app.ai"
    app.write_text(
        'identity "User":\n'
        '  field "role" is text must be present\n\n'
        'flow "demo": requires identity.role is "admin"\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    (root / "packages").mkdir()
    (root / "namel3ss.lock.json").write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")


def test_why_payload_schema(tmp_path: Path) -> None:
    _write_basic_app(tmp_path)
    payload = get_why_payload(str(tmp_path / "app.ai"))
    assert payload["schema_version"] == 1
    assert payload["flows"] == 1
    assert payload["pages"] == 0
    assert payload["records"] == 0
