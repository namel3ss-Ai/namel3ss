from __future__ import annotations

from pathlib import Path

from namel3ss.performance.profiler import profile_app_build


def _write_demo_app(path: Path) -> None:
    path.write_text(
        'spec is "1.0"\n\n'
        'page "home":\n'
        '  title is "Dashboard"\n'
        '  text is "Welcome"\n',
        encoding="utf-8",
    )


def test_profile_app_build_has_stable_stage_order(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_demo_app(app_path)

    profile = profile_app_build(app_path, iterations=2, enabled=True)
    assert profile.enabled is True
    assert profile.iterations == 2
    assert [item.stage for item in profile.metrics] == [
        "load_program",
        "build_manifest",
        "serialize_manifest",
    ]
    assert profile.page_count == 1
    assert profile.element_count >= 2
    assert profile.manifest_bytes > 0


def test_profile_app_build_disabled_returns_empty_metrics(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_demo_app(app_path)

    profile = profile_app_build(app_path, iterations=3, enabled=False)
    assert profile.enabled is False
    assert profile.iterations == 3
    assert profile.page_count == 0
    assert profile.manifest_bytes == 0
    assert all(item.elapsed_ms == 0.0 for item in profile.metrics)


def test_profile_app_build_shape_is_repeatable(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_demo_app(app_path)

    first = profile_app_build(app_path, iterations=1, enabled=True)
    second = profile_app_build(app_path, iterations=1, enabled=True)
    assert [item.stage for item in first.metrics] == [item.stage for item in second.metrics]
    assert first.page_count == second.page_count
    assert first.element_count == second.element_count
    assert first.action_count == second.action_count
    assert first.manifest_bytes == second.manifest_bytes
