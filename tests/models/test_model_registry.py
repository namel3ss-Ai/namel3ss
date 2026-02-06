from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.models import add_registry_entry, deprecate_registry_entry, load_model_registry, resolve_model_entry


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_registry_add_list_resolve_and_deprecate(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    path, created = add_registry_entry(
        project_root=tmp_path,
        app_path=app,
        name="gpt-4",
        version="1.0",
        provider="openai",
        domain="general",
        tokens_per_second=50,
        cost_per_token=0.00001,
        privacy_level="standard",
        status="active",
    )
    assert path.exists()
    assert created.ref() == "gpt-4@1.0"

    registry = load_model_registry(tmp_path, app)
    assert registry.find("gpt-4") is not None
    assert registry.find("gpt-4@1.0") is not None
    assert resolve_model_entry(project_root=tmp_path, app_path=app, reference="gpt-4@1.0") is not None

    _, deprecated = deprecate_registry_entry(project_root=tmp_path, app_path=app, name="gpt-4", version="1.0")
    assert deprecated.status == "deprecated"
    reloaded = load_model_registry(tmp_path, app)
    assert reloaded.find("gpt-4@1.0") is not None
    assert reloaded.find("gpt-4@1.0").status == "deprecated"


def test_registry_rejects_duplicate_entries(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    add_registry_entry(
        project_root=tmp_path,
        app_path=app,
        name="gpt-4",
        version="1.0",
        provider="openai",
        domain="general",
        tokens_per_second=50,
        cost_per_token=0.00001,
        privacy_level="standard",
        status="active",
    )
    with pytest.raises(Namel3ssError):
        add_registry_entry(
            project_root=tmp_path,
            app_path=app,
            name="gpt-4",
            version="1.0",
            provider="openai",
            domain="general",
            tokens_per_second=50,
            cost_per_token=0.00001,
            privacy_level="standard",
            status="active",
        )
