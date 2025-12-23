from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from namel3ss.editor.server import EditorServer


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str) -> dict:
    with urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_editor_server_health_and_diagnose(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(app, 'flow "demo":\n  return "ok"\n')
    server = EditorServer(app, port=0)
    server.start(background=True)
    try:
        base = f"http://127.0.0.1:{server.bound_port}"
        health = _get(f"{base}/health")
        assert health["status"] == "ok"
        diag = _post(f"{base}/diagnose", {})
        assert "diagnostics" in diag
    finally:
        server.shutdown()
