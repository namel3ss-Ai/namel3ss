from __future__ import annotations

from namel3ss.parser.decl.page_story import parse_story_block


def parse_story_item(parser, *, allow_pattern_params: bool = False):
    return parse_story_block(parser, allow_pattern_params=allow_pattern_params)


__all__ = ["parse_story_item"]
