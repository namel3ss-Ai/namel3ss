from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.purity import is_pure, pure_effect_message


def require_effect_allowed(ctx, *, effect: str, line: int | None, column: int | None) -> None:
    flow = getattr(ctx, "flow", None)
    if not flow or not is_pure(getattr(flow, "purity", None)):
        return
    raise Namel3ssError(
        pure_effect_message(effect, flow_name=getattr(flow, "name", None)),
        line=line if line is not None else getattr(flow, "line", None),
        column=column if column is not None else getattr(flow, "column", None),
    )


__all__ = ["require_effect_allowed"]
