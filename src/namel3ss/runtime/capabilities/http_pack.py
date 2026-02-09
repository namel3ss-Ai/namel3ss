from __future__ import annotations

from namel3ss.runtime.capabilities.pack_model import (
    PACK_PURITY_EFFECTFUL,
    PACK_REPLAY_VERIFY,
    CapabilityPack,
    build_capability_pack,
)


def http_capability_pack() -> CapabilityPack:
    return build_capability_pack(
        name="http_client",
        version="1.0.0",
        provided_actions=("http.get", "http.post"),
        required_permissions=("http",),
        runtime_bindings={
            "executor": "namel3ss.runtime.capabilities.http_client",
            "trace_type": "capability_usage",
        },
        effect_capabilities=("network",),
        contract_version="runtime-ui@1",
        purity=PACK_PURITY_EFFECTFUL,
        replay_mode=PACK_REPLAY_VERIFY,
    )


__all__ = ["http_capability_pack"]
