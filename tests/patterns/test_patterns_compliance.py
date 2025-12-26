import json
from pathlib import Path

from namel3ss.patterns.index import load_patterns


def test_pattern_lockfile_license_rules():
    for pattern in load_patterns():
        lock_path = pattern.path / "namel3ss.lock.json"
        assert lock_path.exists(), f"Missing lockfile: {lock_path}"
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        packages = data.get("packages", []) if isinstance(data, dict) else []
        for pkg in packages:
            license_id = pkg.get("license") or pkg.get("license_file")
            assert license_id, f"Package license missing in {pattern.id}"
