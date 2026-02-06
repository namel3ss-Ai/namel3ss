from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.quality import run_quality_checks, suggest_quality_fixes


def _write_quality(tmp_path: Path) -> None:
    (tmp_path / "quality.yaml").write_text(
        "naming_convention: snake_case\n"
        "max_field_length: 64\n"
        "required_fields:\n"
        "  - id\n"
        "  - email\n"
        "disallowed_prompt_words:\n"
        "  - violent\n",
        encoding="utf-8",
    )


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'record "user_profile":\n'
        "  id is text\n\n"
        'prompt "unsafe_prompt":\n'
        '  version is "1.0.0"\n'
        '  text is "This language is violent."\n'
        '  description is "Prompt"\n\n'
        'flow "BadFlow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    return app


def test_quality_checks_detect_naming_required_and_bias_issues(tmp_path: Path) -> None:
    _write_quality(tmp_path)
    app = _write_app(tmp_path)
    source = app.read_text(encoding="utf-8")
    report = run_quality_checks(source, project_root=tmp_path, app_path=app)
    assert report["ok"] is False
    codes = {
        str(issue.get("code"))
        for issue in report.get("issues", [])
        if isinstance(issue, dict)
    }
    assert "quality.naming" in codes
    assert "quality.required_field_missing" in codes
    assert "quality.bias_word" in codes
    fixes = suggest_quality_fixes(report)
    assert fixes


def test_quality_invalid_config_errors(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    (tmp_path / "quality.yaml").write_text("unknown_key: true\n", encoding="utf-8")
    with pytest.raises(Namel3ssError):
        run_quality_checks(app.read_text(encoding="utf-8"), project_root=tmp_path, app_path=app)


def test_quality_supports_nested_sections_format(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    (tmp_path / "quality.yaml").write_text(
        "naming:\n"
        "  enforce_snake_case: true\n"
        "schema:\n"
        "  max_field_length: 64\n"
        "  required_fields:\n"
        "    - id\n"
        "    - email\n"
        "prompts:\n"
        "  disallow_words:\n"
        "    - violent\n",
        encoding="utf-8",
    )
    report = run_quality_checks(app.read_text(encoding="utf-8"), project_root=tmp_path, app_path=app)
    assert report["ok"] is False
    codes = {
        str(issue.get("code"))
        for issue in report.get("issues", [])
        if isinstance(issue, dict)
    }
    assert "quality.naming" in codes
    assert "quality.required_field_missing" in codes
    assert "quality.bias_word" in codes
