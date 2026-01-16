from __future__ import annotations

import json
import socket
import time
import urllib.request
from pathlib import Path

from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.builds import load_build_metadata, read_latest_build_id
from namel3ss.runtime.production_server import ProductionRunner


APP_SOURCE = '''spec is "1.0"

flow "echo":
  return input.message

page "Home":
  button "Send":
    calls flow "echo"
'''


def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def _fetch_json(url: str) -> dict:
    return json.loads(_fetch_text(url))


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _wait_for_health(port: int) -> None:
    for _ in range(10):
        try:
            payload = _fetch_json(f"http://127.0.0.1:{port}/health")
            if payload.get("ok") is True:
                return
        except Exception:
            time.sleep(0.05)
    raise AssertionError("Production server not ready")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_production_server_serves_build_assets(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    assert run_build_command([app_path.as_posix(), "--target", "service"]) == 0
    build_id = read_latest_build_id(tmp_path, "service")
    assert build_id
    build_path, meta = load_build_metadata(tmp_path, "service", build_id)
    app_relative = meta.get("app_relative_path")
    assert isinstance(app_relative, str)
    artifacts = meta.get("artifacts") if isinstance(meta, dict) else None
    runner = ProductionRunner(
        build_path,
        tmp_path / app_relative,
        build_id=build_id,
        port=_free_port(),
        artifacts=artifacts if isinstance(artifacts, dict) else None,
    )
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        html = _fetch_text(f"http://127.0.0.1:{port}/")
        expected = (build_path / "web" / "index.html").read_text(encoding="utf-8")
        assert html == expected
        assert "devOverlay" not in html
        assert "runtime-badge" not in html

        js = _fetch_text(f"http://127.0.0.1:{port}/runtime.js")
        assert js == (build_path / "web" / "runtime.js").read_text(encoding="utf-8")

        payload = _fetch_json(f"http://127.0.0.1:{port}/api/ui")
        assert payload.get("pages")

        response = _post_json(
            f"http://127.0.0.1:{port}/api/action",
            {"id": "page.home.button.send", "payload": {"message": "hi"}},
        )
        assert response.get("ok") is True
        assert response.get("result") == "hi"
    finally:
        runner.shutdown()
