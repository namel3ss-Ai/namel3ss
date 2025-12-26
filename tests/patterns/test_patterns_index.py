from pathlib import Path

from namel3ss.patterns.index import load_patterns


def test_patterns_index_and_layout():
    patterns = load_patterns()
    assert len(patterns) >= 5
    for pattern in patterns:
        assert pattern.path.exists(), f"Missing pattern directory: {pattern.path}"
        assert (pattern.path / "app.ai").exists()
        assert (pattern.path / "modules").exists()
        assert (pattern.path / "tests").exists()
        assert (pattern.path / "namel3ss.toml").exists()
        assert (pattern.path / "namel3ss.lock.json").exists()
        assert (pattern.path / "packages").exists()
