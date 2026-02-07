from __future__ import annotations

from pathlib import Path

from namel3ss.plugin.trust import (
    compute_tree_hash,
    is_extension_trusted,
    load_trusted_extensions,
    revoke_extension,
    trust_extension,
    trust_store_path,
)


def test_trust_store_round_trip(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)
    record = trust_extension(
        project_root,
        name="charts",
        version="0.1.0",
        digest="deadbeef",
        permissions=("ui", "memory:read"),
        author="Jane Doe",
    )
    path = trust_store_path(project_root)
    assert path.exists()
    loaded = load_trusted_extensions(project_root)
    assert len(loaded) == 1
    assert loaded[0].name == "charts"
    assert loaded[0].version == "0.1.0"
    assert loaded[0].hash == "deadbeef"
    assert loaded[0].permissions == ("ui", "memory:read")
    assert is_extension_trusted(project_root, name=record.name, version=record.version, digest=record.hash)

    removed = revoke_extension(project_root, name="charts", version="0.1.0")
    assert removed == 1
    assert load_trusted_extensions(project_root) == []


def test_tree_hash_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "a.txt").write_text("one", encoding="utf-8")
    (root / "dir").mkdir()
    (root / "dir" / "b.txt").write_text("two", encoding="utf-8")
    first = compute_tree_hash(root)
    second = compute_tree_hash(root)
    assert first == second
