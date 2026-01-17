from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.expr_check_mode import EXPR_CHECK_SCHEMA_VERSION
from namel3ss.contract.model import CONTRACT_SPEC_VERSION
from namel3ss.evals.model import EVAL_SCHEMA_VERSION
from namel3ss.production_contract import PRODUCTION_CONTRACT_VERSION
from namel3ss.release.runner import RELEASE_SCHEMA_VERSION
from namel3ss.runtime.errors.explain import builder as errors_builder
from namel3ss.runtime.flow.explain import builder as flow_builder
from namel3ss.runtime.memory import api as memory_api
from namel3ss.runtime.tools.explain import builder as tools_builder
from namel3ss.runtime.ui.explain import builder as ui_builder
from namel3ss.schema.evolution import SCHEMA_SNAPSHOT_VERSION

ROOT = Path(__file__).resolve().parents[2]


def _assert_stable(value: str, label: str) -> None:
    lowered = value.lower()
    assert ".v" not in lowered, f"{label} contains a version marker: {value}"
    assert "phase" not in lowered, f"{label} contains a phase marker: {value}"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_identifier_constants_are_stable() -> None:
    values = {
        "flow api_version": flow_builder.API_VERSION,
        "errors api_version": errors_builder.API_VERSION,
        "ui api_version": ui_builder.API_VERSION,
        "tools api_version": tools_builder.API_VERSION,
        "memory api_version": memory_api.API_VERSION,
        "production contract schema_version": PRODUCTION_CONTRACT_VERSION,
        "contract spec_version": CONTRACT_SPEC_VERSION,
        "evals schema_version": EVAL_SCHEMA_VERSION,
        "records schema_version": SCHEMA_SNAPSHOT_VERSION,
        "release schema_version": RELEASE_SCHEMA_VERSION,
        "expression schema_version": EXPR_CHECK_SCHEMA_VERSION,
    }
    for label, value in values.items():
        assert isinstance(value, str) and value, f"{label} must be a non-empty string"
        _assert_stable(value, label)


def test_public_identifier_catalogs_are_stable() -> None:
    beta_path = ROOT / "resources" / "beta_surfaces.json"
    beta_payload = _load_json(beta_path)
    schema_version = beta_payload.get("schema_version") or ""
    _assert_stable(str(schema_version), f"{beta_path.as_posix()}:schema_version")
    for entry in beta_payload.get("surfaces") or []:
        if not isinstance(entry, dict):
            continue
        version = entry.get("version")
        if isinstance(version, str) and version:
            _assert_stable(version, f"{beta_path.as_posix()}:{entry.get('id')}")

    for rel_path in (
        "evals/suite.json",
        "tests/perf_baselines/agent_stack.json",
        "tests/fixtures/eval_report_golden.json",
    ):
        payload = _load_json(ROOT / rel_path)
        value = payload.get("schema_version")
        if isinstance(value, str) and value:
            _assert_stable(value, f"{rel_path}:schema_version")
