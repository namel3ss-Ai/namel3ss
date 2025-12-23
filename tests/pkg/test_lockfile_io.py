from pathlib import Path

from namel3ss.pkg.lockfile import lockfile_to_dict, write_lockfile
from namel3ss.pkg.types import ChecksumEntry, DependencySpec, Lockfile, LockedPackage, SourceSpec


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
