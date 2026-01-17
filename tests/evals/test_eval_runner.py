from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.evals.loader import load_eval_suite
from namel3ss.evals.runner import run_eval_suite
from namel3ss.errors.base import Namel3ssError


def _write_basic_app(root: Path) -> None:
    app_dir = root / "apps" / "basic"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "app.ai").write_text(
        "spec is \"1.0\"\n\n"
        "flow \"demo\":\n"
        "  let total is 2 + 3\n"
        "  return total\n",
        encoding="utf-8",
    )


def _write_tool_app(root: Path) -> None:
    app_dir = root / "apps" / "tool_call"
    tools_dir = app_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "echo_tool.py").write_text(
        "def run(payload):\n"
        "    text = payload.get(\"text\", \"\")\n"
        "    return {\"message\": str(text)}\n",
        encoding="utf-8",
    )
    (app_dir / "app.ai").write_text(
        "spec is \"1.0\"\n\n"
        "tool \"echo tool\":\n"
        "  implemented using python\n\n"
        "  input:\n"
        "    text is text\n\n"
        "  output:\n"
        "    message is text\n\n"
        "flow \"demo\":\n"
        "  let result is echo tool:\n"
        "    text is \"hi\"\n"
        "  return result\n",
        encoding="utf-8",
    )


def _write_suite(root: Path, *, mismatch: bool = False) -> Path:
    suite = {
        "schema_version": "evals",
        "thresholds": {"success_rate": 1.0, "max_policy_violations": 0},
        "cases": [
            {
                "id": "basic_math",
                "app": "apps/basic/app.ai",
                "flow": "demo",
                "expect": {"result": 4 if mismatch else 5},
                "tags": ["fast"],
            },
            {
                "id": "tool_call",
                "app": "apps/tool_call/app.ai",
                "flow": "demo",
                "expect": {"result": {"message": "hi"}, "tool_calls": ["echo tool"]},
                "tool_bindings": {
                    "echo tool": {"kind": "python", "entry": "tools.echo_tool:run"}
                },
            },
        ],
    }
    suite_path = root / "suite.json"
    suite_path.write_text(json.dumps(suite, indent=2, sort_keys=True), encoding="utf-8")
    return suite_path


def test_eval_report_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "evals"
    _write_basic_app(root)
    _write_tool_app(root)
    suite_path = _write_suite(root)
    suite = load_eval_suite(suite_path)
    report_a = run_eval_suite(suite)
    report_b = run_eval_suite(suite)
    assert report_a.as_dict() == report_b.as_dict()


def test_eval_fast_filter(tmp_path: Path) -> None:
    root = tmp_path / "evals"
    _write_basic_app(root)
    _write_tool_app(root)
    suite_path = _write_suite(root)
    suite = load_eval_suite(suite_path)
    report = run_eval_suite(suite, fast=True)
    assert report.summary["cases"] == 1
    assert report.cases[0].case_id == "basic_math"


def test_eval_missing_suite(tmp_path: Path) -> None:
    with pytest.raises(Namel3ssError):
        load_eval_suite(tmp_path)


def test_eval_thresholds_fail(tmp_path: Path) -> None:
    root = tmp_path / "evals"
    _write_basic_app(root)
    _write_tool_app(root)
    suite_path = _write_suite(root, mismatch=True)
    suite = load_eval_suite(suite_path)
    report = run_eval_suite(suite)
    assert report.status == "fail"
