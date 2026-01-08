from __future__ import annotations

from namel3ss.runtime.memory_packs.format import MemoryPack
from namel3ss.runtime.memory_packs.render import (
    override_summary_lines,
    pack_diff_lines,
    pack_loaded_lines,
    pack_order_lines,
)
from namel3ss.runtime.memory_packs.sources import OverrideEntry, SourceMap
from namel3ss.traces.builders import (
    build_memory_pack_loaded,
    build_memory_pack_merged,
    build_memory_pack_overrides,
)


def build_pack_loaded_event(*, pack: MemoryPack) -> dict:
    return build_memory_pack_loaded(
        pack_id=pack.pack_id,
        pack_version=pack.pack_version,
        title="Memory pack loaded",
        lines=pack_loaded_lines(pack),
    )


def build_pack_merged_event(*, packs: list[MemoryPack], sources: SourceMap | None = None) -> dict:
    lines = list(pack_order_lines(packs))
    if sources is not None:
        lines.extend(pack_diff_lines(sources))
    return build_memory_pack_merged(
        title="Memory packs merged",
        lines=lines,
    )


def build_pack_overrides_event(*, overrides: list[OverrideEntry]) -> dict:
    return build_memory_pack_overrides(
        title="Memory pack overrides",
        lines=override_summary_lines(overrides),
    )


__all__ = ["build_pack_loaded_event", "build_pack_merged_event", "build_pack_overrides_event"]
