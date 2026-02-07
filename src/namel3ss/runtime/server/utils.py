from __future__ import annotations

import json
from typing import IO, Any, Mapping

from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry


def read_json_body(headers: Mapping[str, str], rfile: IO[bytes]) -> dict | None:
    length = int(headers.get("Content-Length", "0"))
    raw_body = rfile.read(length) if length else b""
    try:
        decoded = raw_body.decode("utf-8") if raw_body else ""
        return json.loads(decoded or "{}")
    except json.JSONDecodeError:
        return None


def get_or_create_route_registry(server: Any) -> RouteRegistry:
    registry = getattr(server, "route_registry", None)
    if registry is None:
        registry = RouteRegistry()
        server.route_registry = registry  # type: ignore[attr-defined]
    return registry


def dispatch_dynamic_route(
    *,
    registry: RouteRegistry,
    method: str,
    raw_path: str,
    headers: dict[str, str],
    rfile: IO[bytes],
    program: Any,
    state: Any,
    store: Any,
    flow_executor: Any,
    identity: dict | None = None,
    auth_context: object | None = None,
):
    revision = getattr(state, "revision", None) if state else None
    refresh_routes(program=program, registry=registry, revision=revision, logger=print)
    return dispatch_route(
        registry=registry,
        method=method,
        raw_path=raw_path,
        headers=headers,
        rfile=rfile,
        program=program,
        identity=identity,
        auth_context=auth_context,
        store=store,
        flow_executor=flow_executor,
    )


__all__ = ["dispatch_dynamic_route", "get_or_create_route_registry", "read_json_body"]
