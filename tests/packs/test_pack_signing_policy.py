from __future__ import annotations

import shutil
from pathlib import Path

from namel3ss.runtime.packs.policy import PackTrustPolicy, evaluate_policy
from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key
from namel3ss.runtime.packs.verification import load_pack_verification


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "packs_authoring"


def test_pack_signature_rejects_tamper(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    shutil.copytree(FIXTURES_ROOT / "pack_python_local", pack_dir)
    add_trusted_key(tmp_path, TrustedKey(key_id="test.key", public_key="secret"))
    manifest_path = pack_dir / "pack.yaml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    verification = load_pack_verification(pack_dir, manifest_text, None, app_root=tmp_path)
    assert verification.verified is True
    manifest_path.write_text(manifest_text + "\n# tampered\n", encoding="utf-8")
    verification = load_pack_verification(pack_dir, manifest_path.read_text(encoding="utf-8"), None, app_root=tmp_path)
    assert verification.verified is False


def test_pack_policy_blocks_signer_and_capabilities() -> None:
    policy = PackTrustPolicy(
        allow_unverified_installs=False,
        allow_unverified_enable=False,
        max_risk="high",
        allowed_capabilities={"filesystem": "read", "network": "none", "env": "none", "subprocess": "none"},
        allowed_signers=["official.key"],
        allowed_packs=None,
        source_path=Path("policy.toml"),
    )
    decision = evaluate_policy(
        policy,
        operation="install",
        verified=True,
        risk="low",
        capabilities={"filesystem": "write", "network": "none", "env": "none", "subprocess": "none", "secrets": []},
        pack_id="sample.pack",
        signer_id="test.key",
    )
    assert decision.allowed is False
    assert "signer is not allowed by policy" in decision.reasons
    assert "filesystem=write exceeds allowed read" in decision.reasons
