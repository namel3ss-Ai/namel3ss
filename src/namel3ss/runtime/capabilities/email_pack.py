from __future__ import annotations

from namel3ss.runtime.capabilities.pack_model import (
    PACK_PURITY_EFFECTFUL,
    PACK_REPLAY_VERIFY,
    CapabilityPack,
    build_capability_pack,
)


def email_capability_pack() -> CapabilityPack:
    return build_capability_pack(
        name="email_sender",
        version="1.0.0",
        provided_actions=("email.dry_run", "email.send"),
        required_permissions=("secrets", "third_party_apis"),
        runtime_bindings={
            "executor": "namel3ss.runtime.capabilities.email_sender",
            "trace_type": "capability_usage",
        },
        effect_capabilities=("network", "secrets"),
        contract_version="runtime-ui@1",
        purity=PACK_PURITY_EFFECTFUL,
        replay_mode=PACK_REPLAY_VERIFY,
    )


__all__ = ["email_capability_pack"]
