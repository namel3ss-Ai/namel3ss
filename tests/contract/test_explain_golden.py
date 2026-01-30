from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from namel3ss.cli.explain_mode import build_explain_payload
from namel3ss.determinism import canonical_json_dumps

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "explain"
APP_FIXTURE = FIXTURE_DIR / "basic.ai"
GOLDEN_PATH = FIXTURE_DIR / "basic.json"

_ENV_KEYS = {
    "NAMEL3SS_OLLAMA_HOST",
    "NAMEL3SS_OLLAMA_TIMEOUT_SECONDS",
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_OPENAI_BASE_URL",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "N3_PERSIST_TARGET",
    "N3_PERSIST",
    "N3_DB_PATH",
    "N3_DATABASE_URL",
    "N3_EDGE_KV_URL",
    "N3_REPLICA_URLS",
    "N3_PYTHON_TOOL_TIMEOUT_SECONDS",
    "N3_TOOL_SERVICE_URL",
    "N3_FOREIGN_STRICT",
    "N3_FOREIGN_ALLOW",
    "N3_IDENTITY_JSON",
    "N3_IDENTITY_ROLE",
    "N3_AUTH_SIGNING_KEY",
    "N3_AUTH_ALLOW_IDENTITY",
    "N3_AUTH_USERNAME",
    "N3_AUTH_PASSWORD",
    "N3_AUTH_IDENTITY_JSON",
    "N3_AUTH_CREDENTIALS_JSON",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "OPENAI_API_KEY",
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "N3_AUTH_SIGNING_KEY",
    "N3_PROFILE",
}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("N3_IDENTITY_") or key.startswith("N3_AUTH_"):
            monkeypatch.delenv(key, raising=False)
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _prepare_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.ai").write_text(APP_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "namel3ss.toml").write_text(
        "[authentication]\npassword = \"SECRET_TOKEN\"\n",
        encoding="utf-8",
    )
    proof_dir = root / ".namel3ss" / "proofs"
    run_dir = root / ".namel3ss" / "run"
    proof_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        root / ".namel3ss" / "active_proof.json",
        {"proof_id": "proof-stable", "target": "local", "build_id": None},
    )
    _write_json(
        proof_dir / "proof-stable.json",
        {
            "proof_id": "proof-stable",
            "schema_version": 1,
            "persistence": {"target": "memory", "descriptor": None},
            "identity": {
                "requires": {"flows": ["restricted"], "pages": ["home"], "flow_count": 1, "page_count": 1},
                "tenant_scoping": {"records": ["Account"], "count": 1},
            },
            "capsules": {
                "modules": [
                    {"name": "local_core", "source": {"kind": "local"}},
                    {"name": "pack_tools", "source": {"kind": "package"}},
                ]
            },
            "governance": {"status": "unknown", "checks": []},
        },
    )
    _write_json(
        run_dir / "last.json",
        {
            "ok": False,
            "flow_name": "restricted",
            "traces": [
                {
                    "type": "flow_call_started",
                    "flow_call_id": "flow_call:0001",
                    "caller_flow": "restricted",
                    "callee_flow": "alpha",
                    "inputs": ["x"],
                    "outputs": ["result"],
                    "contract_inputs": ["x"],
                    "contract_outputs": ["result"],
                },
                {
                    "type": "flow_call_finished",
                    "flow_call_id": "flow_call:0001",
                    "caller_flow": "restricted",
                    "callee_flow": "alpha",
                    "status": "error",
                    "error_message": "failed at /Users/example/app.ai with SECRET_TOKEN",
                },
                {
                    "type": "pipeline_started",
                    "pipeline": "retrieval",
                    "steps": [
                        {"step_id": "pipeline:retrieval:accept:1", "step_kind": "accept", "ordinal": 1}
                    ],
                },
                {
                    "type": "pipeline_step",
                    "pipeline": "retrieval",
                    "step_id": "pipeline:retrieval:accept:1",
                    "step_kind": "accept",
                    "status": "ok",
                    "summary": {"query": "invoice", "limit": 1, "note": "SECRET_TOKEN"},
                    "checksum": "abc123",
                    "ordinal": 1,
                },
                {"type": "pipeline_finished", "pipeline": "retrieval", "status": "ok"},
            ],
        },
    )
    return root / "app.ai"


def test_explain_payload_matches_golden_and_is_deterministic(tmp_path: Path) -> None:
    app_path = _prepare_project(tmp_path / "explain")
    payload_first = build_explain_payload(app_path)
    payload_second = build_explain_payload(app_path)
    actual_first = canonical_json_dumps(payload_first, pretty=True, drop_run_keys=False)
    actual_second = canonical_json_dumps(payload_second, pretty=True, drop_run_keys=False)
    assert actual_first == actual_second
    expected = GOLDEN_PATH.read_text(encoding="utf-8")
    assert actual_first == expected
    assert "SECRET_TOKEN" not in actual_first
    assert "/Users/" not in actual_first
    assert "C:\\" not in actual_first
    assert "***REDACTED***" in actual_first
    assert "<path>" in actual_first


def test_explain_profile_is_opt_in_and_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import namel3ss.profiling as profiling

    app_path = _prepare_project(tmp_path / "explain_profile")
    monkeypatch.setenv("N3_PROFILE", "1")
    profiling.reset()
    payload_first = build_explain_payload(app_path)
    payload_second = build_explain_payload(app_path)
    profile_first = payload_first.get("profiling")
    profile_second = payload_second.get("profiling")
    assert profile_first == profile_second
    assert isinstance(profile_first, dict)
    buckets = profile_first.get("buckets") if isinstance(profile_first, dict) else None
    assert isinstance(buckets, list)
    names = [bucket.get("name") for bucket in buckets if isinstance(bucket, dict)]
    assert names == sorted(names)
    assert {"scan", "parse", "lower", "explain"} <= set(names)
    stripped = dict(payload_first)
    stripped.pop("profiling", None)
    expected = GOLDEN_PATH.read_text(encoding="utf-8")
    assert canonical_json_dumps(stripped, pretty=True, drop_run_keys=False) == expected
    actual = canonical_json_dumps(payload_first, pretty=True, drop_run_keys=False)
    assert "SECRET_TOKEN" not in actual
    assert "/Users/" not in actual
    assert "C:\\" not in actual
