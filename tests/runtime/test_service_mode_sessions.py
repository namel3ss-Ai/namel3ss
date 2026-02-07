from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.service_runner import ServiceRunner


SERVICE_APP = '''spec is "1.0"

capabilities:
  service
  multi_user
  remote_studio

flow "set_note":
  set state.note is input.note
  return state.note

page "home":
  button "Save":
    calls flow "set_note"
'''


ROLE_APP = '''spec is "1.0"

capabilities:
  service
  multi_user

flow "check":
  if session.role is not "admin":
    return "forbidden"
  return "ok"

page "home":
  button "Check":
    calls flow "check"
'''


SERVICE_ONLY_APP = '''spec is "1.0"

capabilities:
  service

flow "demo":
  return "ok"
'''


NO_SERVICE_APP = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _fetch_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url=url, method="GET")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request) as response:  # noqa: S310
        body = response.read().decode("utf-8")
    return json.loads(body)


def _post_json(url: str, payload: dict, *, headers: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Content-Length", str(len(data)))
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request) as response:  # noqa: S310
        body = response.read().decode("utf-8")
    return json.loads(body)


def _delete_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url=url, method="DELETE")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request) as response:  # noqa: S310
        body = response.read().decode("utf-8")
    return json.loads(body)


def _wait_for_health(port: int) -> None:
    for _ in range(20):
        try:
            payload = _fetch_json(f"http://127.0.0.1:{port}/health")
            if payload.get("ok") is True:
                return
        except Exception:
            pass
        time.sleep(0.05)
    raise AssertionError("service runner not ready")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        return int(sock.getsockname()[1])


def test_service_sessions_are_isolated_and_remotely_inspectable(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SERVICE_APP, encoding="utf-8")
    runner = ServiceRunner(app_path, "service", port=_free_port())
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)

        session_one = _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "user"})
        session_two = _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "admin"})
        session_one_id = str(session_one.get("session_id"))
        session_two_id = str(session_two.get("session_id"))
        assert session_one_id != session_two_id

        action_url = f"http://127.0.0.1:{port}/api/action"
        result_one = _post_json(
            action_url,
            {"id": "page.home.button.save", "payload": {"note": "alpha"}},
            headers={"X-N3-Session-Id": session_one_id},
        )
        result_two = _post_json(
            action_url,
            {"id": "page.home.button.save", "payload": {"note": "beta"}},
            headers={"X-N3-Session-Id": session_two_id},
        )
        assert result_one.get("ok") is True
        assert result_two.get("ok") is True

        state_one = _fetch_json(f"http://127.0.0.1:{port}/api/ui/state?session_id={session_one_id}")
        state_two = _fetch_json(f"http://127.0.0.1:{port}/api/ui/state?session_id={session_two_id}")
        assert state_one["state"]["values"].get("note") == "alpha"
        assert state_two["state"]["values"].get("note") == "beta"

        listed = _fetch_json(f"http://127.0.0.1:{port}/api/service/sessions")
        listed_ids = [item.get("session_id") for item in listed.get("sessions", [])]
        assert session_one_id in listed_ids
        assert session_two_id in listed_ids

        studio_state = _fetch_json(f"http://127.0.0.1:{port}/api/service/studio/{session_one_id}/state")
        studio_traces = _fetch_json(f"http://127.0.0.1:{port}/api/service/studio/{session_one_id}/traces")
        assert studio_state.get("role") == "user"
        assert studio_state.get("state", {}).get("note") == "alpha"
        assert isinstance(studio_traces.get("traces"), list)
        assert len(studio_traces.get("traces") or []) >= 1

        deleted = _delete_json(f"http://127.0.0.1:{port}/api/service/sessions/{session_one_id}")
        assert deleted.get("ok") is True

        try:
            _fetch_json(f"http://127.0.0.1:{port}/api/service/studio/{session_one_id}/state")
        except urllib.error.HTTPError as err:
            assert err.code == 404
        else:
            raise AssertionError("expected 404 for deleted session")
    finally:
        runner.shutdown()


def test_service_session_role_is_available_in_flow_logic(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(ROLE_APP, encoding="utf-8")
    runner = ServiceRunner(app_path, "service", port=_free_port())
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)

        user_session = _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "user"})
        admin_session = _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "admin"})

        action_url = f"http://127.0.0.1:{port}/api/action"
        user_result = _post_json(
            action_url,
            {"id": "page.home.button.check", "payload": {}},
            headers={"X-N3-Session-Id": str(user_session.get("session_id"))},
        )
        admin_result = _post_json(
            action_url,
            {"id": "page.home.button.check", "payload": {}},
            headers={"X-N3-Session-Id": str(admin_session.get("session_id"))},
        )
        assert user_result.get("result") == "forbidden"
        assert admin_result.get("result") == "ok"
    finally:
        runner.shutdown()


def test_service_without_multi_user_rejects_second_session(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SERVICE_ONLY_APP, encoding="utf-8")
    runner = ServiceRunner(app_path, "service", port=_free_port())
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)

        _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "user"})
        try:
            _post_json(f"http://127.0.0.1:{port}/api/service/sessions", {"role": "admin"})
        except urllib.error.HTTPError as err:
            assert err.code == 400
            body = err.read().decode("utf-8", errors="replace")
            assert "multi_user" in body
        else:
            raise AssertionError("expected second session creation to fail")
    finally:
        runner.shutdown()


def test_service_endpoints_are_blocked_without_service_capability(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(NO_SERVICE_APP, encoding="utf-8")
    runner = ServiceRunner(app_path, "service", port=_free_port(), require_service_capability=True)
    with pytest.raises(Namel3ssError) as exc:
        runner.start(background=True)
    assert "service" in exc.value.message.lower()
