from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.ai.model_manager import configure_canary, load_model_manager



def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app



def _write_models(tmp_path: Path) -> None:
    models = tmp_path / ".namel3ss" / "models.yaml"
    models.parent.mkdir(parents=True, exist_ok=True)
    models.write_text(
        "models:\n"
        "  base:\n"
        "    version: 1.0\n"
        "    image: repo/base:1\n"
        "  candidate:\n"
        "    version: 1.1\n"
        "    image: repo/candidate:1\n",
        encoding="utf-8",
    )



def test_model_canary_route_and_disable(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    _write_models(tmp_path)

    configure_canary(
        project_root=app.parent,
        app_path=app,
        primary_model="base",
        candidate_model="candidate",
        fraction=1.0,
        shadow=True,
    )

    manager = load_model_manager(app.parent, app)
    assert manager is not None
    route = manager.route_model("base", key="hello", flow_name="demo")
    assert route.selected_model == "candidate"
    assert route.shadow_model == "base"
    assert route.canary_hit is True

    configure_canary(
        project_root=app.parent,
        app_path=app,
        primary_model="base",
        candidate_model=None,
        fraction=0.0,
        shadow=False,
    )
    manager = load_model_manager(app.parent, app)
    assert manager is not None
    route = manager.route_model("base", key="hello", flow_name="demo")
    assert route.selected_model == "base"
    assert route.shadow_model is None
    assert route.canary_hit is False
