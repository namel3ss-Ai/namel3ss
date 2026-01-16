from __future__ import annotations

import json
from pathlib import Path


def test_governance_proof_build_metadata_present() -> None:
    root = Path(__file__).resolve().parents[2]
    proof_root = root / "spec" / "programs" / "governance" / "proof" / "build" / "local"
    _assert_build_metadata(proof_root)


def test_governance_verify_build_metadata_present() -> None:
    root = Path(__file__).resolve().parents[2]
    verify_root = root / "spec" / "programs" / "governance" / "verify" / "build" / "local"
    _assert_build_metadata(verify_root)


def _assert_build_metadata(root: Path) -> None:
    latest = root / "latest.json"
    build = root / "spec" / "build.json"
    assert latest.exists(), f"Missing {latest}"
    assert build.exists(), f"Missing {build}"
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    build_payload = json.loads(build.read_text(encoding="utf-8"))
    assert latest_payload.get("build_id") == "spec"
    assert build_payload.get("build_id") == "spec"
    assert isinstance(build_payload.get("lockfile_digest"), str) and build_payload["lockfile_digest"]
