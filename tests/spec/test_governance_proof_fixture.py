from __future__ import annotations

import json
from pathlib import Path


_SNAPSHOT_MODES = {"proof", "verify"}


def test_spec_program_build_metadata_present() -> None:
    root = Path(__file__).resolve().parents[2]
    programs_root = root / "spec" / "programs"
    for spec_path in sorted(programs_root.rglob("app.spec.json")):
        meta = _load_spec_meta(spec_path)
        mode = meta.get("mode")
        if mode not in _SNAPSHOT_MODES:
            continue
        target = str(meta.get("target", "local"))
        app_root = spec_path.parent
        build_root = app_root / "build" / target
        app_path = app_root / "app.ai"
        _assert_build_metadata(build_root, app_path, target, repo_root=root)


def _load_spec_meta(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _assert_build_metadata(build_root: Path, app_path: Path, target: str, *, repo_root: Path) -> None:
    latest = build_root / "latest.json"
    build = build_root / "spec" / "build.json"
    rel_app = _relative_path(app_path, repo_root)
    regenerate = f"python3 tools/spec_build_snapshot.py {rel_app} --target {target}"
    assert latest.exists(), f"Missing {latest}. Regenerate with `{regenerate}`."
    assert build.exists(), f"Missing {build}. Regenerate with `{regenerate}`."
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    build_payload = json.loads(build.read_text(encoding="utf-8"))
    assert latest_payload.get("build_id") == "spec"
    assert build_payload.get("build_id") == "spec"
    assert isinstance(build_payload.get("lockfile_digest"), str) and build_payload["lockfile_digest"]
