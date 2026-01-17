from __future__ import annotations

from pathlib import Path


def test_report_artifacts_live_in_runtime_or_goldens() -> None:
    root = Path(__file__).resolve().parents[2]
    allowed_roots = {
        root / "tests" / "fixtures",
        root / "tests" / "golden",
        root / "tests" / "memory_proof" / "golden",
    }
    offenders: list[str] = []
    for pattern in ("*report*.json", "*report*.txt"):
        for path in root.rglob(pattern):
            if not path.is_file():
                continue
            if ".git" in path.parts or ".venv" in path.parts:
                continue
            if ".namel3ss" in path.parts:
                continue
            if any(allowed in path.parents for allowed in allowed_roots):
                continue
            if _is_under_build_dir(path, root / "patterns"):
                continue
            if _is_under_build_dir(path, root / "spec"):
                continue
            offenders.append(path.relative_to(root).as_posix())
    assert not offenders, "Report artifacts must stay under runtime or golden paths:\n" + "\n".join(sorted(offenders))


def _is_under_build_dir(path: Path, base: Path) -> bool:
    try:
        rel = path.relative_to(base)
    except ValueError:
        return False
    return "build" in rel.parts
