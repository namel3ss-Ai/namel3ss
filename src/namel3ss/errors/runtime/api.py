from __future__ import annotations

from namel3ss.errors.runtime.builder import build_error_pack
from namel3ss.errors.runtime.model import ErrorPack, RuntimeWhere
from namel3ss.errors.runtime.render_plain import render_error_plain, render_fix_text


def build_runtime_error(
    *,
    boundary: str,
    err: Exception,
    where: RuntimeWhere,
    traces: list[dict] | None = None,
) -> tuple[ErrorPack, str, str]:
    pack = build_error_pack(boundary=boundary, err=err, where=where, traces=traces)
    return pack, render_error_plain(pack), render_fix_text(pack)


__all__ = ["build_runtime_error"]
