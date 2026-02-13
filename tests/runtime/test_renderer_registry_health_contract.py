from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.ui.renderer.manifest_parity_guard import verify_renderer_manifest_parity
from namel3ss.runtime.ui.renderer.registry_health_contract import (
    RENDERER_REGISTRY_HEALTH_SCHEMA_VERSION,
    build_renderer_registry_health_payload,
)


def test_renderer_registry_health_payload_contract_shape() -> None:
    payload = build_renderer_registry_health_payload()
    assert payload.get("schema_version") == RENDERER_REGISTRY_HEALTH_SCHEMA_VERSION
    assert isinstance(payload.get("ok"), bool)

    registry = payload.get("registry")
    assert isinstance(registry, dict)
    assert isinstance(registry.get("renderer_ids"), list)
    assert registry.get("renderer_ids") == sorted(registry.get("renderer_ids", []))
    assert registry.get("required_renderer_ids") == sorted(registry.get("required_renderer_ids", []))

    parity = payload.get("parity")
    assert isinstance(parity, dict)
    assert isinstance(parity.get("manifest_hash"), str)
    assert isinstance(parity.get("registry_manifest_hash"), str)


def test_renderer_registry_health_payload_canonical_json_is_stable() -> None:
    first = canonical_json_dumps(
        build_renderer_registry_health_payload(),
        pretty=False,
        drop_run_keys=False,
    )
    second = canonical_json_dumps(
        build_renderer_registry_health_payload(),
        pretty=False,
        drop_run_keys=False,
    )
    assert first == second


def test_renderer_manifest_parity_guard_reports_matching_hashes() -> None:
    parity = verify_renderer_manifest_parity()
    assert parity.ok is True
    assert len(parity.manifest_hash) == 64
    assert parity.manifest_hash == parity.registry_manifest_hash
