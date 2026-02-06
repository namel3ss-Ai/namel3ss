import json
from pathlib import Path

from namel3ss.pkg.lockfile import UNIFIED_LOCKFILE_FILENAME, lockfile_to_dict, read_lockfile, write_lockfile
from namel3ss.pkg.types import ChecksumEntry, DependencySpec, Lockfile, LockedPackage, RuntimeLockEntry, SourceSpec


def test_lockfile_orders_roots_and_packages(tmp_path: Path) -> None:
    alpha_source = SourceSpec(scheme="github", owner="owner", repo="alpha", ref="v0.1.0")
    zeta_source = SourceSpec(scheme="github", owner="owner", repo="zeta", ref="v0.2.0")
    lockfile = Lockfile(
        lockfile_version=1,
        roots=[
            DependencySpec(name="zeta", source=zeta_source),
            DependencySpec(name="alpha", source=alpha_source),
        ],
        packages=[
            LockedPackage(
                name="zeta",
                version="0.2.0",
                source=zeta_source,
                license_id="MIT",
                license_file=None,
                checksums=[ChecksumEntry(path="capsule.ai", sha256="a" * 64)],
                dependencies=[],
            ),
            LockedPackage(
                name="alpha",
                version="0.1.0",
                source=alpha_source,
                license_id="Apache-2.0",
                license_file=None,
                checksums=[ChecksumEntry(path="capsule.ai", sha256="b" * 64)],
                dependencies=[],
            ),
        ],
    )
    payload = lockfile_to_dict(lockfile)
    assert [root["name"] for root in payload["roots"]] == ["alpha", "zeta"]
    assert [pkg["name"] for pkg in payload["packages"]] == ["alpha", "zeta"]


def test_lockfile_write_is_stable(tmp_path: Path) -> None:
    source = SourceSpec(scheme="github", owner="owner", repo="demo", ref="v0.1.0")
    lockfile = Lockfile(
        lockfile_version=1,
        roots=[DependencySpec(name="demo", source=source)],
        packages=[
            LockedPackage(
                name="demo",
                version="0.1.0",
                source=source,
                license_id="MIT",
                license_file=None,
                checksums=[ChecksumEntry(path="capsule.ai", sha256="c" * 64)],
                dependencies=[],
            )
        ],
    )
    path = write_lockfile(tmp_path, lockfile)
    first = path.read_text(encoding="utf-8")
    path = write_lockfile(tmp_path, lockfile)
    second = path.read_text(encoding="utf-8")
    assert first == second


def test_lockfile_runtime_section_is_serialized(tmp_path: Path) -> None:
    source = SourceSpec(scheme="github", owner="owner", repo="demo", ref="v0.1.0")
    lockfile = Lockfile(
        lockfile_version=1,
        roots=[DependencySpec(name="demo", source=source)],
        packages=[],
        python_packages=[
            RuntimeLockEntry(
                name="requests",
                version="2.31.0",
                checksum="a" * 64,
                source="pypi",
                dependencies={},
                trust_tier="community",
            )
        ],
        system_packages=[
            RuntimeLockEntry(
                name="postgresql-client",
                version="13",
                checksum="b" * 64,
                source="system",
                dependencies={},
                trust_tier="informational",
            )
        ],
    )
    payload = lockfile_to_dict(lockfile)
    assert "runtime" in payload
    assert payload["runtime"]["python"][0]["name"] == "requests"
    assert payload["runtime"]["system"][0]["name"] == "postgresql-client"

    path = write_lockfile(tmp_path, lockfile)
    assert path.name == "namel3ss.lock.json"
    assert (tmp_path / UNIFIED_LOCKFILE_FILENAME).exists()


def test_read_lockfile_prefers_unified_filename(tmp_path: Path) -> None:
    payload = {
        "lockfile_version": 1,
        "roots": [],
        "packages": [],
    }
    (tmp_path / UNIFIED_LOCKFILE_FILENAME).write_text(json.dumps(payload), encoding="utf-8")
    lockfile = read_lockfile(tmp_path)
    assert lockfile.lockfile_version == 1
