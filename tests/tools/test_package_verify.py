from __future__ import annotations

import importlib.util
import sys
import shutil
from pathlib import Path


def _load_module():
    path = Path("tools/package_verify.py").resolve()
    spec = importlib.util.spec_from_file_location("package_verify", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_package_verify_plan_is_temp_root(tmp_path: Path) -> None:
    module = _load_module()
    plan = module.plan_paths()
    try:
        assert tmp_path not in plan.temp_root.parents
        assert tmp_path not in plan.stage_dir.parents
        assert tmp_path not in plan.dist_dir.parents
        assert tmp_path not in plan.venv_dir.parents
    finally:
        shutil.rmtree(plan.temp_root, ignore_errors=True)


def test_package_verify_main_cleans_temp(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    captured: dict[str, Path] = {}

    def fake_plan_paths():
        temp_root = tmp_path / "pkg-temp"
        stage_dir = temp_root / "stage"
        dist_dir = temp_root / "dist"
        venv_dir = temp_root / "venv"
        temp_root.mkdir(parents=True, exist_ok=True)
        captured["temp_root"] = temp_root
        return module.PackagePlan(temp_root=temp_root, stage_dir=stage_dir, dist_dir=dist_dir, venv_dir=venv_dir)

    def fake_stage_repo(_repo_root: Path, stage_dir: Path) -> None:
        stage_dir.mkdir(parents=True, exist_ok=True)

    def fake_build_wheel(_stage_dir: Path, dist_dir: Path) -> Path:
        dist_dir.mkdir(parents=True, exist_ok=True)
        wheel = dist_dir / "namel3ss-temp.whl"
        wheel.write_text("wheel", encoding="utf-8")
        return wheel

    def fake_verify_wheel(_plan, _wheel_path) -> None:
        return None

    monkeypatch.setattr(module, "plan_paths", fake_plan_paths)
    monkeypatch.setattr(module, "stage_repo", fake_stage_repo)
    monkeypatch.setattr(module, "build_wheel", fake_build_wheel)
    monkeypatch.setattr(module, "verify_wheel", fake_verify_wheel)
    monkeypatch.setattr(module, "_build_native", lambda _stage: None)
    monkeypatch.delenv("N3_BUILD_NATIVE", raising=False)

    rc = module.main([])
    assert rc == 0
    assert "temp_root" in captured
    assert not captured["temp_root"].exists()
