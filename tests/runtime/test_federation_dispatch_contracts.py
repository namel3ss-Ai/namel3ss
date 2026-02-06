from __future__ import annotations

import io
import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry


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


def _program(tmp_path: Path) -> tuple[Path, object]:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    program, _ = load_program(app.as_posix())
    return app, program


def _write_tenants(tmp_path: Path) -> None:
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


def _cross_tenant_identity() -> dict[str, object]:
    return {
        "subject": "alice",
        "tenant": "acme",
        "tenant_id": "acme",
        "tenants": ["acme", "beta"],
    }


def _dispatch(registry: RouteRegistry, program, *, tenant: str, identity: dict[str, object]):
    return dispatch_route(
        registry=registry,
        method="GET",
        raw_path=f"/api/echo?tenant={tenant}",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=identity,
        auth_context=None,
        store=None,
    )


def test_cross_tenant_route_requires_federation_contract(tmp_path: Path) -> None:
    app_path, program = _program(tmp_path)
    _write_tenants(tmp_path)
    registry = RouteRegistry()
    registry.update(program.routes)

    denied = _dispatch(registry, program, tenant="beta", identity=_cross_tenant_identity())
    assert denied is not None
    assert denied.status == 403
    assert isinstance(denied.payload, dict)
    assert "federation" in str(denied.payload.get("message", "")).lower()

    (tmp_path / "federation.yaml").write_text(
        (
            "contracts:\n"
                "  - source_tenant: acme\n"
                "    target_tenant: beta\n"
                "    flow_name: echo\n"
                "    output_schema:\n"
                "      result: text\n"
            "    auth:\n"
            "      client_id: acme_beta_client\n"
            "    rate_limit:\n"
            "      calls_per_minute: 1\n"
        ),
        encoding="utf-8",
    )

    allowed = _dispatch(registry, program, tenant="beta", identity=_cross_tenant_identity())
    assert allowed is not None
    assert allowed.status == 200
    assert allowed.payload == {"result": "ok"}

    usage_path = tmp_path / ".namel3ss" / "federation_usage.jsonl"
    rows = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    assert rows[0]["contract_id"] == "acme->beta:echo"

    limited = _dispatch(registry, program, tenant="beta", identity=_cross_tenant_identity())
    assert limited is not None
    assert limited.status == 429
    assert isinstance(limited.payload, dict)
    assert "rate" in str(limited.payload.get("message", "")).lower()

    audit_path = tmp_path / ".namel3ss" / "audit.jsonl"
    audit_rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(audit_rows) >= 2
    latest = audit_rows[-1]
    details = latest.get("details") if isinstance(latest, dict) else {}
    assert isinstance(details, dict)
    assert details.get("federated") is True
    assert details.get("source_tenant") == "acme"
    assert details.get("target_tenant") == "beta"
