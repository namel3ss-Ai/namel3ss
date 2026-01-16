from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _lockfile_digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def _resolve_app_path(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_dir():
        candidate = candidate / "app.ai"
    return candidate


def _write_snapshot(app_path: Path, target: str) -> None:
    lock_path = app_path.parent / "namel3ss.lock.json"
    if not lock_path.exists():
        raise SystemExit(f"Missing lockfile: {lock_path}")
    digest = _lockfile_digest(lock_path)
    build_root = app_path.parent / "build" / target
    _write_json(build_root / "latest.json", {"build_id": "spec"})
    _write_json(
        build_root / "spec" / "build.json",
        {"build_id": "spec", "lockfile_digest": digest},
    )


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: python3 tools/spec_build_snapshot.py path/to/app.ai [--target local]")
        return 2
    target = "local"
    app_paths: list[Path] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--target":
            if i + 1 >= len(argv):
                print("Missing value for --target.")
                return 2
            target = argv[i + 1]
            i += 2
            continue
        app_paths.append(_resolve_app_path(arg))
        i += 1
    for app_path in app_paths:
        if not app_path.exists():
            print(f"Missing app: {app_path}")
            return 2
        _write_snapshot(app_path, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
