from __future__ import annotations

from namel3ss.runtime.capabilities.pack_model import (
    PACK_PURITY_EFFECTFUL,
    PACK_REPLAY_VERIFY,
    CapabilityPack,
    build_capability_pack,
)


def sql_capability_pack() -> CapabilityPack:
    return build_capability_pack(
        name="sql_database",
        version="1.0.0",
        provided_actions=("sql.query_readonly",),
        required_permissions=("files",),
        runtime_bindings={
            "executor": "namel3ss.runtime.capabilities.sql_database",
            "trace_type": "capability_usage",
        },
        effect_capabilities=("filesystem_read",),
        contract_version="runtime-ui@1",
        purity=PACK_PURITY_EFFECTFUL,
        replay_mode=PACK_REPLAY_VERIFY,
    )


__all__ = ["sql_capability_pack"]
