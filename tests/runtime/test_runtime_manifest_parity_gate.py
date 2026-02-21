from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.server.headless_api import build_manifest_hash
from namel3ss.runtime.server.startup.startup_context import (
    RUNTIME_MANIFEST_DRIFT_ERROR_CODE,
    build_static_startup_manifest_payload,
    require_static_runtime_manifest_parity,
)
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _load_program(tmp_path: Path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    return load_project(app_path).program


def test_manifest_parity_gate_accepts_matching_static_and_runtime_hashes(tmp_path: Path) -> None:
    program = _load_program(tmp_path)
    app_path = getattr(program, "app_path", None)
    project_root = getattr(program, "project_root", None)
    config = load_config(app_path=app_path, root=project_root)
    identity = resolve_identity(
        config,
        getattr(program, "identity", None),
        mode=ValidationMode.RUNTIME,
    )
    runtime_manifest = build_manifest(
        program,
        config=config,
        state={},
        store=None,
        identity=identity,
        mode=ValidationMode.RUNTIME,
        display_mode="production",
        diagnostics_enabled=False,
    )
    runtime_hash = build_manifest_hash(runtime_manifest)
    observed_hash = require_static_runtime_manifest_parity(
        program=program,
        runtime_manifest_payload=runtime_manifest,
        ui_mode="production",
        diagnostics_enabled=False,
    )
    assert observed_hash == runtime_hash


def test_manifest_parity_gate_rejects_startup_hash_drift(tmp_path: Path) -> None:
    program = _load_program(tmp_path)
    runtime_manifest = build_static_startup_manifest_payload(
        program,
        ui_mode="production",
        diagnostics_enabled=False,
    )
    drifted_manifest = dict(runtime_manifest)
    drifted_manifest["__drift__"] = "1"
    with pytest.raises(Namel3ssError) as exc:
        require_static_runtime_manifest_parity(
            program=program,
            runtime_manifest_payload=drifted_manifest,
            ui_mode="production",
            diagnostics_enabled=False,
        )
    assert RUNTIME_MANIFEST_DRIFT_ERROR_CODE in str(exc.value)
