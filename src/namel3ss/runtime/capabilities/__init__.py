__all__ = [
    "CapabilityContext",
    "EffectiveGuarantees",
    "build_effective_guarantees",
    "resolve_tool_capabilities",
    "summarize_guarantees",
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
    raise AttributeError(f"module 'namel3ss.runtime.capabilities' has no attribute {name!r}")
