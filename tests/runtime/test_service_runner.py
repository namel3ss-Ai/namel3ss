import json
import time
import urllib.request

from namel3ss.runtime.service_runner import ServiceRunner


APP_SOURCE = '''flow "demo":
  return "ok"
'''


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def test_service_runner_health_and_version(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(APP_SOURCE, encoding="utf-8")
    runner = ServiceRunner(app, "service", build_id="service-test", port=0)
    runner.start(background=True)
    port = runner.bound_port
    payload = {}
    for _ in range(10):
        try:
            payload = _fetch_json(f"http://127.0.0.1:{port}/health")
            break
        except Exception:
            time.sleep(0.05)
    assert payload.get("ok") is True
    assert payload.get("build_id") == "service-test"
    version_payload = _fetch_json(f"http://127.0.0.1:{port}/version")
    assert version_payload.get("version")
    runner.shutdown()
