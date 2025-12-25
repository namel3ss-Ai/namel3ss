from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.runners.base import ToolRunner
from namel3ss.runtime.tools.runners.container_runner import ContainerRunner
from namel3ss.runtime.tools.runners.local_runner import LocalRunner
from namel3ss.runtime.tools.runners.service_runner import ServiceRunner


_RUNNERS: dict[str, ToolRunner] = {
    "local": LocalRunner(),
    "service": ServiceRunner(),
    "container": ContainerRunner(),
}


def get_runner(name: str) -> ToolRunner:
    runner = _RUNNERS.get(name)
    if runner is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown tool runner '{name}'.",
                why="Supported runners are local, service, and container.",
                fix="Update the binding runner or remove the runner field.",
                example='runner: "local"',
            )
        )
    return runner


def list_runners() -> list[str]:
    return sorted(_RUNNERS.keys())


__all__ = ["get_runner", "list_runners"]
