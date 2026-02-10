from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.create import scaffold_rag_chat_app
from namel3ss.cli.generate_theme import scaffold_theme_config
from namel3ss.cli.create_mode import run_create_command


def test_scaffold_rag_chat_app_dry_run_is_deterministic(tmp_path: Path) -> None:
    first = scaffold_rag_chat_app("Support Assistant", tmp_path, dry_run=True)
    second = scaffold_rag_chat_app("Support Assistant", tmp_path, dry_run=True)
    assert first.target == second.target
    assert first.files == second.files
    assert "app.ai" in first.files
    assert "patterns/rag_chat.json" in first.files


def test_scaffold_rag_chat_app_writes_expected_files(tmp_path: Path) -> None:
    result = scaffold_rag_chat_app("Support Assistant", tmp_path, dry_run=False)
    assert (result.target / "app.ai").exists()
    assert (result.target / "patterns" / "rag_chat.json").exists()
    assert (result.target / "docs" / "notes.md").exists()


def test_run_create_command_supports_rag_app_json_output(tmp_path: Path, capsys) -> None:
    previous = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        status = run_create_command(["rag_app", "helpdesk", "--dry-run", "--json"])
    finally:
        os.chdir(previous)
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "rag_app"
    assert payload["dry_run"] is True
    assert "patterns/rag_chat.json" in payload["files"]


def test_scaffold_theme_config_and_create_command(tmp_path: Path, capsys) -> None:
    dry_run = scaffold_theme_config("Brand Theme", tmp_path, base_theme="dark", dry_run=True)
    assert dry_run.target.name == "brand_theme.json"
    assert dry_run.files == ("themes/brand_theme.json",)

    previous = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        status = run_create_command(["theme", "Brand Theme", "high_contrast", "--json"])
    finally:
        os.chdir(previous)
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "theme"
    assert payload["name"] == "brand_theme"
    assert payload["path"].endswith("themes/brand_theme.json")


def test_run_create_command_supports_rag_app_profiling_flag(tmp_path: Path, capsys) -> None:
    previous = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        status = run_create_command(["rag_app", "opsdesk", "--with-profiling", "--json"])
    finally:
        os.chdir(previous)
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["options"]["with_profiling"] is True
    assert "tools/profile_app.py" in payload["files"]
