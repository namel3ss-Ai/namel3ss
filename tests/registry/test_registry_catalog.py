from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.registry.catalog import build_catalog
from namel3ss.runtime.registry.search import select_best_entry
from namel3ss.runtime.registry.trust_evaluator import evaluate_registry_trust


def test_registry_catalog_ordering_deterministic(tmp_path: Path) -> None:
    entries = [
        _entry("pack.beacon", "Beacon Pack", "0.1.0", "sha256:bbb"),
        _entry("pack.anchor", "Anchor Pack", "0.2.0", "sha256:aaa"),
        _entry("pack.anchor", "Anchor Pack", "0.1.0", "sha256:aab"),
    ]
    policy = load_pack_policy(tmp_path)
    packs = build_catalog(entries, policy=policy, installed_versions={}, app_root=tmp_path)
    assert [pack.pack_id for pack in packs] == ["pack.anchor", "pack.beacon"]
    anchor_versions = [version["pack_version"] for version in packs[0].versions]
    assert anchor_versions == ["0.2.0", "0.1.0"]


def test_version_selection_is_deterministic(tmp_path: Path) -> None:
    entries = [
        _entry("pack.core", "Core Pack", "0.1.0", "sha256:111"),
        _entry("pack.core", "Core Pack", "0.3.0", "sha256:333"),
        _entry("pack.core", "Core Pack", "0.2.0", "sha256:222"),
    ]
    policy = load_pack_policy(tmp_path)
    match = select_best_entry(entries, pack_id="pack.core", pack_version=None, policy=policy)
    assert match is not None
    assert match.entry.get("pack_version") == "0.3.0"


def test_registry_trust_decision_stable(tmp_path: Path) -> None:
    policy_path = tmp_path / ".namel3ss" / "trust" / "policy.toml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        'allow_unverified_installs = true\nmax_risk = "high"\nallowed_capabilities = { network = "outbound" }\n',
        encoding="utf-8",
    )
    policy = load_pack_policy(tmp_path)
    entry = _entry("pack.unverified", "Unverified Pack", "0.1.0", "sha256:abc", verified=False)
    decision = evaluate_registry_trust(entry, policy=policy, app_root=tmp_path)
    assert decision.status == "untrusted"
    assert decision.policy_status == "allowed"
    assert decision.policy_reasons[:2] == ["unverified allowed by policy", "risk low within policy"]


def _entry(
    pack_id: str,
    pack_name: str,
    version: str,
    digest: str,
    *,
    verified: bool = True,
) -> dict[str, object]:
    return {
        "entry_version": 1,
        "pack_id": pack_id,
        "pack_name": pack_name,
        "pack_version": version,
        "pack_digest": digest,
        "intent_text": f"Intent for {pack_id}.",
        "risk": "low",
        "signer_id": "maintainer",
        "verified_by": ["maintainer"] if verified else [],
        "signature": {"status": "verified" if verified else "unverified", "algorithm": "hmac-sha256"},
        "tools": ["tool one"],
        "intent_tags": ["tool", "pack"],
        "intent_phrases": ["Provide tools."],
        "capabilities": {
            "filesystem": "none",
            "network": "none",
            "env": "none",
            "subprocess": "none",
            "secrets": [],
        },
        "runner": {"default": "local", "service_url": None, "container_image": None},
        "source": {"kind": "local_file", "uri": f"{pack_id}.n3pack.zip"},
    }
