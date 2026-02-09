__all__ = [
    "CapabilityContext",
    "EffectiveGuarantees",
    "attach_capability_contract_fields",
    "attach_capability_manifest_fields",
    "build_effective_guarantees",
    "extract_capability_usage",
    "list_capability_packs",
    "resolve_tool_capabilities",
    "summarize_guarantees",
    "validate_capability_packs",
]


def __getattr__(name: str):
    if name in {"CapabilityContext", "EffectiveGuarantees"}:
        from namel3ss.runtime.capabilities.model import CapabilityContext, EffectiveGuarantees

        return {"CapabilityContext": CapabilityContext, "EffectiveGuarantees": EffectiveGuarantees}[name]
    if name in {"build_effective_guarantees", "resolve_tool_capabilities", "summarize_guarantees"}:
        from namel3ss.runtime.capabilities.effective import (
            build_effective_guarantees,
            resolve_tool_capabilities,
            summarize_guarantees,
        )

        return {
            "build_effective_guarantees": build_effective_guarantees,
            "resolve_tool_capabilities": resolve_tool_capabilities,
            "summarize_guarantees": summarize_guarantees,
        }[name]
    if name in {"attach_capability_contract_fields", "attach_capability_manifest_fields", "extract_capability_usage"}:
        from namel3ss.runtime.capabilities.contract_fields import (
            attach_capability_contract_fields,
            attach_capability_manifest_fields,
            extract_capability_usage,
        )

        return {
            "attach_capability_contract_fields": attach_capability_contract_fields,
            "attach_capability_manifest_fields": attach_capability_manifest_fields,
            "extract_capability_usage": extract_capability_usage,
        }[name]
    if name in {"list_capability_packs"}:
        from namel3ss.runtime.capabilities.registry import list_capability_packs

        return {"list_capability_packs": list_capability_packs}[name]
    if name in {"validate_capability_packs"}:
        from namel3ss.runtime.capabilities.validation import validate_capability_packs

        return {"validate_capability_packs": validate_capability_packs}[name]
    raise AttributeError(f"module 'namel3ss.runtime.capabilities' has no attribute {name!r}")
