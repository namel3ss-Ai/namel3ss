import hashlib
import json
import subprocess
from pathlib import Path

from namel3ss.cli.builds import load_build_metadata, read_latest_build_id
from namel3ss.patterns.index import load_patterns
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


def test_pattern_lockfile_license_rules():
    for pattern in load_patterns():
        lock_path = pattern.path / "namel3ss.lock.json"
        assert lock_path.exists(), f"Missing lockfile: {lock_path}"
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        packages = data.get("packages", []) if isinstance(data, dict) else []
        for pkg in packages:
            license_id = pkg.get("license") or pkg.get("license_file")
            assert license_id, f"Package license missing in {pattern.id}"


def test_pattern_build_snapshots_present() -> None:
    target = "local"
    for pattern in load_patterns():
        lock_path = pattern.path / LOCKFILE_FILENAME
        digest = _lockfile_digest(lock_path)
        build_id = read_latest_build_id(pattern.path, target)
        assert build_id, _snapshot_missing_message(pattern.id, pattern.path, target)
        try:
            _, meta = load_build_metadata(pattern.path, target, build_id)
        except Exception as err:
            raise AssertionError(_snapshot_missing_message(pattern.id, pattern.path, target)) from err
        assert meta.get("lockfile_digest") == digest, _snapshot_mismatch_message(pattern.id, pattern.path, target)


def _lockfile_digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _snapshot_missing_message(pattern_id: str, pattern_path: Path, target: str) -> str:
    return (
        f"Missing build snapshot for pattern '{pattern_id}' ({target}). "
        f"Run `n3 pack --target {target}` in {pattern_path.as_posix()} and commit build metadata."
    )


def _snapshot_mismatch_message(pattern_id: str, pattern_path: Path, target: str) -> str:
    return (
        f"Build snapshot lockfile digest mismatch for pattern '{pattern_id}' ({target}). "
        f"Run `n3 pack --target {target}` in {pattern_path.as_posix()} and commit updated build metadata."
    )


def test_pattern_runtime_artifacts_not_tracked() -> None:
    tracked = _tracked_pattern_artifacts()
    unexpected = sorted(
        path for path in tracked if not path.endswith("/.namel3ss/tools.yaml")
    )
    assert not unexpected, _runtime_artifact_message(unexpected)


def _tracked_pattern_artifacts() -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "patterns/**/.namel3ss/**"],
            text=True,
        )
    except Exception as err:
        raise AssertionError("git is required to validate pattern artifacts are not tracked.") from err
    return [line.strip() for line in output.splitlines() if line.strip()]


def _runtime_artifact_message(unexpected: list[str]) -> str:
    preview = "\n".join(f"- {path}" for path in unexpected[:10])
    more = "" if len(unexpected) <= 10 else f"\n- ... and {len(unexpected) - 10} more"
    return (
        "Runtime artifacts under patterns/.namel3ss must not be tracked.\n"
        "Remove them from git and keep only .namel3ss/tools.yaml when needed.\n"
        "Runtime artifacts are ephemeral. Run `python tools/clean_pattern_artifacts.py` "
        "and drop them from the index if they appear again.\n"
        f"{preview}{more}"
    )
