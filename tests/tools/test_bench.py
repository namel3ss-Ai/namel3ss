from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps

FORBIDDEN = ("/Users/", "/home/", "C:\\")


def _load_module():
    path = Path("tools/bench.py").resolve()
    spec = importlib.util.spec_from_file_location("bench", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_bench(module, tmp_path: Path) -> str:
    out_path = tmp_path / "bench_report.json"
    rc = module.main(["--out", str(out_path), "--iterations", "1"])
    assert rc == 0
    return out_path.read_text(encoding="utf-8")


def test_bench_report_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("N3_NATIVE", raising=False)
    monkeypatch.delenv("N3_NATIVE_EXEC", raising=False)
    monkeypatch.delenv("N3_NATIVE_LIB", raising=False)
    monkeypatch.delenv("N3_PERSIST_ROOT", raising=False)

    module = _load_module()
    first = _run_bench(module, tmp_path)
    second = _run_bench(module, tmp_path)
    assert first == second

    for marker in FORBIDDEN:
        assert marker not in first
    repo_root = Path(__file__).resolve().parents[2]
    assert str(repo_root) not in first

    data = json.loads(first)
    canonical = canonical_json_dumps(data, pretty=True, drop_run_keys=False)
    assert canonical == first
    assert data.get("timing_mode") == "deterministic"
