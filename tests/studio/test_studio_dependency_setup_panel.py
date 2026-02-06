from pathlib import Path


def test_dependency_setup_panel_wires_dependencies_api() -> None:
    js = Path("src/namel3ss/studio/web/studio/dependency_setup.js").read_text(encoding="utf-8")
    assert "/api/dependencies" in js
    assert "Install dependencies" in js
    assert "Update dependencies" in js
    assert "Dependency graph" in js
    assert "Search dependencies" in js
    assert "remove_python" in js
    assert "remove_system" in js


def test_setup_panel_calls_dependency_setup_module() -> None:
    js = Path("src/namel3ss/studio/web/studio/setup.js").read_text(encoding="utf-8")
    assert "dependencySetup" in js
    assert "refreshDependencies" in js
    assert "renderDependencies" in js
