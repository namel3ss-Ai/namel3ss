from __future__ import annotations

from typing import Callable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.server.startup.startup_context import RuntimeStartupContext


def render_startup_banner(context: RuntimeStartupContext) -> str:
    payload = context.to_dict()
    return f"Runtime startup {canonical_json_dumps(payload, pretty=False, drop_run_keys=False)}"


def print_startup_banner(
    context: RuntimeStartupContext,
    *,
    printer: Callable[[str], None] = print,
) -> None:
    printer(render_startup_banner(context))


__all__ = [
    "print_startup_banner",
    "render_startup_banner",
]
