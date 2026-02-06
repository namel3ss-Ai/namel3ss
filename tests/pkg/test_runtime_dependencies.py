from __future__ import annotations

from namel3ss.pkg.runtime_dependencies import (
    build_runtime_lock_entries,
    normalize_python_spec,
    verify_runtime_lock_entry,
    verify_runtime_lock_entry_with_artifacts,
)
from namel3ss.pkg.types import Manifest


def test_normalize_python_spec_converts_at_version_to_pin() -> None:
    assert normalize_python_spec("requests@2.31.0") == "requests==2.31.0"


def test_build_runtime_lock_entries_is_deterministic() -> None:
    manifest = Manifest(
        runtime_python_dependencies=("httpx@0.27.0", "requests==2.31.0"),
        runtime_system_dependencies=("postgresql-client@13",),
    )
    first = build_runtime_lock_entries(manifest, freeze_lines=["requests==2.31.0", "httpx==0.27.0"])
    second = build_runtime_lock_entries(manifest, freeze_lines=["requests==2.31.0", "httpx==0.27.0"])

    assert [entry.__dict__ for entry in first[0]] == [entry.__dict__ for entry in second[0]]
    assert [entry.__dict__ for entry in first[1]] == [entry.__dict__ for entry in second[1]]
    assert all(verify_runtime_lock_entry(entry) for entry in first[0] + first[1])


def test_runtime_lock_entries_use_artifact_checksums_when_available() -> None:
    manifest = Manifest(
        runtime_python_dependencies=("requests==2.31.0",),
        runtime_system_dependencies=("postgresql-client@13",),
    )
    python_entries, system_entries = build_runtime_lock_entries(
        manifest,
        freeze_lines=["requests==2.31.0"],
        python_artifact_checksums={"requests": "abc123"},
        system_artifact_checksums={"postgresql-client": "def456"},
    )

    assert python_entries[0].checksum == "artifact:abc123"
    assert system_entries[0].checksum == "artifact:def456"
    assert verify_runtime_lock_entry_with_artifacts(
        python_entries[0],
        python_artifact_checksums={"requests": "abc123"},
    )
    assert verify_runtime_lock_entry_with_artifacts(
        system_entries[0],
        system_artifact_checksums={"postgresql-client": "def456"},
    )
