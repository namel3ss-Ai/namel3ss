from __future__ import annotations

import io
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.model import AppConfig
from namel3ss.governance.rbac import add_user, generate_token
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.store.memory_store import MemoryStore


SOURCE = '''spec is "1.0"

flow "echo":
  return "ok"

route "echo_route":
  path is "/api/echo"
  method is "GET"
  request:
    tenant is text
  response:
    result is text
  flow is "echo"
'''


def _program(tmp_path: Path):
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    program, _sources = load_program(app.as_posix())
    return app, program


def test_route_dispatch_enforces_identity_tenant_match(tmp_path: Path) -> None:
    app_path, program = _program(tmp_path)
    (tmp_path / "tenants.yaml").write_text(
        (
            "tenants:\n"
            "  - tenant_id: acme\n"
            "    name: ACME\n"
            "    namespace_prefix: acme_\n"
            "    storage_backend: local\n"
            "  - tenant_id: beta\n"
            "    name: Beta\n"
            "    namespace_prefix: beta_\n"
            "    storage_backend: local\n"
        ),
        encoding="utf-8",
    )
    add_user(project_root=tmp_path, app_path=app_path, username="alice", roles=["developer"], tenant="acme")
    token = generate_token("alice")
    auth = resolve_auth_context(
        {"Authorization": f"Bearer {token}"},
        config=AppConfig(),
        identity_schema=None,
        store=MemoryStore(),
        project_root=tmp_path.as_posix(),
        app_path=app_path.as_posix(),
    )
    assert auth.authenticated is True
    assert auth.identity.get("tenant") == "acme"

    registry = RouteRegistry()
    registry.update(program.routes)

    allowed = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/echo?tenant=acme",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=auth.identity,
        auth_context=auth,
        store=None,
    )
    assert allowed is not None
    assert allowed.status == 200
    assert allowed.payload == {"result": "ok"}

    denied = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/echo?tenant=beta",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=auth.identity,
        auth_context=auth,
        store=None,
    )
    assert denied is not None
    assert denied.status == 403
    assert isinstance(denied.payload, dict)
    assert "tenant" in str(denied.payload.get("message", "")).lower()
