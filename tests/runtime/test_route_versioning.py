from __future__ import annotations

import io
import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.versioning import load_version_config, route_metadata_by_target


SOURCE = '''spec is "1.0"

flow "users_v0_flow":
  return "v0"

flow "users_v1_flow":
  return "v1"

flow "users_v2_flow":
  return "v2"

route "users_v0_route":
  path is "/api/users"
  method is "GET"
  request:
    payload is text
  response:
    value is text
  flow is "users_v0_flow"

route "users_v1_route":
  path is "/api/users"
  method is "GET"
  request:
    payload is text
  response:
    value is text
  flow is "users_v1_flow"

route "users_v2_route":
  path is "/api/users"
  method is "GET"
  request:
    payload is text
  response:
    value is text
  flow is "users_v2_flow"
'''


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    (tmp_path / "versions.yaml").write_text(
        "routes:\n"
        "  users:\n"
        '    - version: "0.9"\n'
        '      status: "removed"\n'
        '      target: "users_v0_route"\n'
        '      replacement: "2.0"\n'
        '      deprecation_date: "2026-06-01"\n'
        '    - version: "1.0"\n'
        '      status: "deprecated"\n'
        '      target: "users_v1_route"\n'
        '      replacement: "2.0"\n'
        '      deprecation_date: "2026-06-01"\n'
        '    - version: "2.0"\n'
        '      status: "active"\n'
        '      target: "users_v2_route"\n',
        encoding="utf-8",
    )
    return app


def test_versioned_route_selection_and_deprecation_headers(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    program, _ = load_program(app.as_posix())
    registry = RouteRegistry()
    config = load_version_config(tmp_path, app)
    registry.update(program.routes, route_version_meta=route_metadata_by_target(config))

    latest = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/users",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert latest is not None
    assert latest.status == 200
    assert latest.payload == {"value": "v2"}
    assert latest.headers is None

    deprecated = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/users",
        headers={"Accept-Version": "1.0"},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert deprecated is not None
    assert deprecated.status == 200
    assert deprecated.payload == {"value": "v1"}
    assert isinstance(deprecated.headers, dict)
    assert "X-N3-Deprecation-Warning" in deprecated.headers

    removed = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/users",
        headers={"Accept-Version": "0.9"},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert removed is not None
    assert removed.status == 404
    assert isinstance(removed.headers, dict)
    assert "X-N3-Deprecation-Warning" in removed.headers

    log_path = tmp_path / ".namel3ss" / "deprecations.jsonl"
    assert log_path.exists()
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert rows[0]["requested_version"] == "1.0"
