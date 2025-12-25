from __future__ import annotations

from namel3ss.runtime.packs.manifest import PackManifest
from namel3ss.runtime.tools.bindings_yaml import ToolBinding


def pack_runner_default(manifest: PackManifest, bindings: dict[str, ToolBinding]) -> str:
    runners = pack_runner_modes(manifest, bindings)
    if "container" in runners:
        return "container"
    if "service" in runners:
        return "service"
    return "local"


def pack_runner_modes(manifest: PackManifest, bindings: dict[str, ToolBinding]) -> set[str]:
    modes: set[str] = set()
    if bindings:
        for binding in bindings.values():
            if binding.runner:
                modes.add(binding.runner)
            elif manifest.runners_default:
                modes.add(manifest.runners_default)
            else:
                modes.add("local")
    elif manifest.runners_default:
        modes.add(manifest.runners_default)
    else:
        modes.add("local")
    return modes


__all__ = ["pack_runner_default", "pack_runner_modes"]
