from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.server.startup.startup_banner import render_startup_banner
from namel3ss.runtime.server.startup.startup_context import (
    RuntimeStartupContext,
    build_runtime_startup_context,
)


def test_runtime_startup_banner_contains_required_contract_fields() -> None:
    context = RuntimeStartupContext(
        app_path="/workspace/app.ai",
        bind_host="127.0.0.1",
        bind_port=7340,
        mode="run",
        headless=False,
        manifest_hash="m" * 64,
        renderer_registry_hash="r" * 64,
        renderer_registry_status="validated",
        lock_path="/tmp/runtime.lock.json",
        lock_pid=111,
    )
    line = render_startup_banner(context)
    assert line.startswith("Runtime startup ")
    payload = json.loads(line.replace("Runtime startup ", "", 1))
    assert payload["app_path"] == "/workspace/app.ai"
    assert payload["bind_host"] == "127.0.0.1"
    assert payload["bind_port"] == 7340
    assert payload["manifest_hash"] == "m" * 64
    assert payload["renderer_registry_hash"] == "r" * 64
    assert payload["renderer_registry_status"] == "validated"
    assert payload["lock_pid"] == 111


def test_runtime_startup_context_manifest_hash_is_order_invariant(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    first = build_runtime_startup_context(
        app_path=app_path,
        bind_host="127.0.0.1",
        bind_port=7360,
        mode="run",
        headless=True,
        manifest_payload={"actions": {"run": {}}, "pages": []},
        lock_path=None,
        lock_pid=0,
        validate_registry=False,
    )
    second = build_runtime_startup_context(
        app_path=app_path,
        bind_host="127.0.0.1",
        bind_port=7360,
        mode="run",
        headless=True,
        manifest_payload={"pages": [], "actions": {"run": {}}},
        lock_path=None,
        lock_pid=0,
        validate_registry=False,
    )
    assert first.manifest_hash == second.manifest_hash
    assert len(first.manifest_hash) == 64
    assert first.renderer_registry_status in {"available", "unavailable"}
