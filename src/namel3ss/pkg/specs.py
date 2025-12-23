from __future__ import annotations

import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.types import SourceSpec


SOURCE_RE = re.compile(r"^github:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)@(?P<ref>.+)$")


def parse_source_spec(text: str) -> SourceSpec:
    raw = text.strip()
    match = SOURCE_RE.match(raw)
    if not match:
        raise Namel3ssError(
            build_guidance_message(
                what="Dependency source is not valid.",
                why="Sources must be in the form github:owner/repo@ref.",
                fix="Use a GitHub source with an explicit tag or sha.",
                example="github:namel3ss-ai/inventory@v0.1.0",
            )
        )
    owner = match.group("owner")
    repo = match.group("repo")
    ref = match.group("ref")
    if not owner or not repo or not ref:
        raise Namel3ssError(
            build_guidance_message(
                what="Dependency source is missing required parts.",
                why="Sources must include owner, repo, and ref.",
                fix="Provide a full GitHub source.",
                example="github:namel3ss-ai/inventory@v0.1.0",
            )
        )
    return SourceSpec(scheme="github", owner=owner, repo=repo, ref=ref)
