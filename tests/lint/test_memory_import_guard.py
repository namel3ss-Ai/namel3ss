from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_guard():
    repo_root = Path(__file__).resolve().parents[2]
    guard_path = repo_root / "tools" / "memory_import_guard.py"
    spec = importlib.util.spec_from_file_location("memory_import_guard", guard_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, repo_root


def test_memory_import_guard() -> None:
    guard, repo_root = _load_guard()
    violations = guard.find_violations(repo_root / "src")
    if violations:
        details = "\n".join(f"{v.path}:{v.line} {v.module}" for v in violations)
        raise AssertionError(f"Memory import guard failed:\n{details}")
