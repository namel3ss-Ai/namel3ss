from __future__ import annotations

from importlib import import_module
from pathlib import Path

from namel3ss.beta_lock.repo_clean import repo_dirty_entries


def test_runtime_packages_have_init_files() -> None:
    root = Path(__file__).resolve().parents[2]
    native_init = root / "src" / "namel3ss" / "runtime" / "native" / "__init__.py"
    observability_init = root / "src" / "namel3ss" / "runtime" / "observability" / "__init__.py"
    assert native_init.exists()
    assert observability_init.exists()
    assert not (native_init.parent / "init.py").exists()
    assert not (observability_init.parent / "init.py").exists()


def test_runtime_imports_are_side_effect_free() -> None:
    root = Path(__file__).resolve().parents[2]
    baseline = set(repo_dirty_entries(root))
    import_module("namel3ss.runtime.native")
    import_module("namel3ss.runtime.observability")
    dirty = set(repo_dirty_entries(root))
    assert dirty == baseline
