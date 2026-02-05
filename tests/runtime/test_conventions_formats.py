from __future__ import annotations

import io
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.conventions.toon import decode_toon
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry


SOURCE = '''spec is "1.0"

flow "list_users":
  return map:
    users is list:
      map:
        status is "active"
        name is "A"
      map:
        status is "inactive"
        name is "B"
      map:
        status is "active"
        name is "C"

route "list_users":
  path is "/api/users"
  method is "GET"
  request:
    payload is json
  response:
    users is list<json>
    next_page is number
  flow is "list_users"
'''


def _load(tmp_path: Path) -> object:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    program, _ = load_program(app_path.as_posix())
    return program


def _dispatch(program, *, path: str):
    registry = RouteRegistry()
    registry.update(program.routes)
    return dispatch_route(
        registry=registry,
        method="GET",
        raw_path=path,
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )


def test_conventions_filter_and_pagination(tmp_path: Path) -> None:
    config_dir = tmp_path / ".namel3ss"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "conventions.yaml").write_text(
        "defaults:\n"
        "  pagination: true\n"
        "  page_size_default: 2\n"
        "  page_size_max: 5\n"
        "routes:\n"
        "  list_users:\n"
        "    filter_fields:\n"
        "      - status\n",
        encoding="utf-8",
    )
    program = _load(tmp_path)
    result = _dispatch(program, path="/api/users?filter=status:active&page=1&page_size=1")
    assert result is not None
    assert result.status == 200
    assert result.payload["users"] == [{"status": "active", "name": "A"}]
    assert result.payload["next_page"] == 2


def test_conventions_filter_not_allowed(tmp_path: Path) -> None:
    program = _load(tmp_path)
    result = _dispatch(program, path="/api/users?filter=status:active")
    assert result is not None
    assert result.status == 400
    assert "Filters are not enabled" in result.payload.get("message", "")
    assert {"code", "message", "remediation"} <= set(result.payload.keys())


def test_formats_toon_response(tmp_path: Path) -> None:
    config_dir = tmp_path / ".namel3ss"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "formats.yaml").write_text(
        "routes:\n"
        "  list_users:\n"
        "    - json\n"
        "    - toon\n",
        encoding="utf-8",
    )
    program = _load(tmp_path)
    result = _dispatch(program, path="/api/users?format=toon")
    assert result is not None
    assert result.body is not None
    decoded = decode_toon(result.body.decode("utf-8"))
    assert decoded["users"][0]["name"] == "A"


def test_formats_toon_rejected(tmp_path: Path) -> None:
    program = _load(tmp_path)
    result = _dispatch(program, path="/api/users?format=toon")
    assert result is not None
    assert result.status == 406
    assert {"code", "message", "remediation"} <= set(result.payload.keys())
