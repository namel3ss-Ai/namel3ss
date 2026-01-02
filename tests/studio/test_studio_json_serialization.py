from pathlib import Path

from namel3ss.studio.api import get_summary_payload
from namel3ss.studio.server import to_json_safe
from namel3ss.utils.json_tools import dumps as json_dumps


def test_to_json_safe_converts_paths():
    payload = {
        "file": Path("/tmp/app.ai"),
        "items": [Path("a"), {"nested": Path("b")}],
        "set": {Path("c"), "value"},
        Path("key"): "value",
    }
    safe = to_json_safe(payload)
    json_dumps(safe)
    assert safe["file"] == "/tmp/app.ai"
    assert all(isinstance(item, str) for item in safe["set"])
    assert "key" in safe


def test_summary_payload_is_json_safe(tmp_path: Path):
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    payload = get_summary_payload(app.read_text(encoding="utf-8"), app)
    assert isinstance(payload.get("file"), str)
    json_dumps(to_json_safe(payload))
