from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from namel3ss.runtime.native import loader as native_loader


def test_native_package_marker() -> None:
    root = Path(__file__).resolve().parents[2]
    native_dir = root / "src" / "namel3ss" / "runtime" / "native"
    assert (native_dir / "__init__.py").exists()
    assert not (native_dir / "init.py").exists()


def test_native_import_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_NATIVE", "1")
    monkeypatch.setenv("N3_NATIVE_LIB", "/missing/native")
    native_loader._reset_native_state()
    sys.modules.pop("namel3ss.runtime.native.adapter", None)
    sys.modules.pop("namel3ss.runtime.native", None)
    importlib.import_module("namel3ss.runtime.native")
    assert native_loader._LOAD_ATTEMPTED is False
    assert "namel3ss.runtime.native.adapter" not in sys.modules


def test_chunk_plan_not_loaded_by_default() -> None:
    sys.modules.pop("namel3ss.ingestion.chunk_plan", None)
    sys.modules.pop("namel3ss.ingestion.api", None)
    importlib.import_module("namel3ss.ingestion.api")
    assert "namel3ss.ingestion.chunk_plan" not in sys.modules
