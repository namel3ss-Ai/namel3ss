from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.server.prod.app import ProductionRunner


def test_production_runner_validates_renderer_registry_on_startup(monkeypatch, tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")

    build_root = tmp_path / "build"
    (build_root / "web").mkdir(parents=True, exist_ok=True)
    program_root = build_root / "program"
    program_root.mkdir(parents=True, exist_ok=True)
    (program_root / "app.ai").write_text(app_path.read_text(encoding="utf-8"), encoding="utf-8")

    calls: list[bool] = []
    monkeypatch.setattr(
        "namel3ss.runtime.server.prod.app.validate_renderer_registry_startup",
        lambda: calls.append(True),
    )
    runner = ProductionRunner(
        build_path=build_root,
        app_path=app_path,
        build_id="test-build",
        artifacts={"program": "program", "web": "web"},
    )

    assert calls == [True]
    assert runner.web_root == build_root / "web"
