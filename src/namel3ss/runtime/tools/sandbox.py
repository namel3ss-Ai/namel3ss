from __future__ import annotations

from namel3ss.runtime.tools.bindings_yaml import ToolBinding


def sandbox_enabled(*, resolved_source: str, runner: str, binding: ToolBinding) -> bool:
    if runner != "local":
        return False
    if binding.sandbox is not None:
        return bool(binding.sandbox)
    if resolved_source in {"builtin_pack", "installed_pack"}:
        return True
    return False


__all__ = ["sandbox_enabled"]
