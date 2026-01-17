from __future__ import annotations

from pathlib import Path

from namel3ss.cli.release_check_mode import _parse_args as _parse_release_args
from namel3ss.evals import cli as eval_cli


def test_release_check_defaults_to_runtime_dir() -> None:
    params = _parse_release_args([])
    assert params.json_path == Path(".namel3ss") / "release_report.json"
    assert params.txt_path is None


def test_eval_defaults_to_runtime_dir() -> None:
    params = eval_cli._parse_args([])
    assert params.json_path == eval_cli.DEFAULT_OUTPUT_DIR / eval_cli.DEFAULT_JSON_NAME
    assert params.txt_path is None


def test_eval_out_dir_sets_report_paths() -> None:
    params = eval_cli._parse_args(["--out-dir", ".namel3ss/ci_artifacts"])
    assert params.json_path == Path(".namel3ss/ci_artifacts") / eval_cli.DEFAULT_JSON_NAME
    assert params.txt_path == Path(".namel3ss/ci_artifacts") / eval_cli.DEFAULT_TXT_NAME
