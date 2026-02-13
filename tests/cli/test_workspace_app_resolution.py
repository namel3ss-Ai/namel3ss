from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.main import main
from namel3ss.cli.workspace.app_path_resolution import build_workspace_app_resolution
from namel3ss.cli.workspace.resolution_warning import build_workspace_resolution_warning


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(APP_SOURCE, encoding="utf-8")


def test_workspace_resolution_uses_stable_sort_policy(tmp_path: Path) -> None:
    _write_app(tmp_path / "apps" / "beta" / "app.ai")
    _write_app(tmp_path / "apps" / "alpha" / "app.ai")
    _write_app(tmp_path / "tools" / "runner" / "app.ai")

    resolution = build_workspace_app_resolution(search_root=tmp_path)

    assert resolution.selected_app_path is not None
    assert resolution.selected_app_path.as_posix().endswith("/apps/alpha/app.ai")
    assert [path.as_posix() for path in resolution.candidate_app_paths] == sorted(
        [path.as_posix() for path in resolution.candidate_app_paths]
    )
    assert resolution.warning_required is True


def test_resolve_app_path_emits_workspace_warning_with_alternatives(tmp_path: Path) -> None:
    _write_app(tmp_path / "apps" / "alpha" / "app.ai")
    _write_app(tmp_path / "apps" / "beta" / "app.ai")
    warnings: list[str] = []

    resolved = resolve_app_path(
        None,
        project_root=tmp_path.as_posix(),
        search_parents=False,
        warning_printer=warnings.append,
    )

    assert resolved.as_posix().endswith("/apps/alpha/app.ai")
    assert warnings
    assert "Workspace contains multiple app roots." in warnings[0]
    assert "Selected: apps/alpha/app.ai" in warnings[0]
    assert "Alternatives: apps/beta/app.ai" in warnings[0]


def test_cli_run_with_project_root_prints_selection_warning(tmp_path: Path, capsys) -> None:
    _write_app(tmp_path / "apps" / "alpha" / "app.ai")
    _write_app(tmp_path / "apps" / "beta" / "app.ai")

    code = main(["run", "--project", tmp_path.as_posix(), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["result"] == "ok"
    assert "Workspace contains multiple app roots." in captured.err
    assert "Selected: apps/alpha/app.ai" in captured.err
    assert "Alternatives: apps/beta/app.ai" in captured.err


def test_workspace_warning_text_is_empty_when_not_required(tmp_path: Path) -> None:
    _write_app(tmp_path / "app.ai")
    resolution = build_workspace_app_resolution(search_root=tmp_path)
    message = build_workspace_resolution_warning(resolution)
    assert message == ""
