from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class TargetSpec:
    name: str
    process_model: str
    persistence_default: str
    description: str


TARGETS: Dict[str, TargetSpec] = {
    "local": TargetSpec(
        name="local",
        process_model="dev",
        persistence_default="sqlite",
        description="Developer run mode with live reloads and local persistence.",
    ),
    "service": TargetSpec(
        name="service",
        process_model="service",
        persistence_default="postgres",
        description="Long-running service mode with health endpoints.",
    ),
    "edge": TargetSpec(
        name="edge",
        process_model="edge",
        persistence_default="edge",
        description="Edge-constrained mode (simulated in this release).",
    ),
}

DEFAULT_TARGET = "local"


def parse_target(raw: str | None) -> TargetSpec:
    name = (raw or DEFAULT_TARGET).strip().lower()
    if name in TARGETS:
        return TARGETS[name]
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown target '{raw}'.",
            why="Targets must be one of local, service, or edge.",
            fix="Choose a supported target with --target.",
            example="n3 run --target service",
        )
    )


def target_names() -> list[str]:
    return sorted(TARGETS.keys())


__all__ = ["TargetSpec", "TARGETS", "DEFAULT_TARGET", "parse_target", "target_names"]
