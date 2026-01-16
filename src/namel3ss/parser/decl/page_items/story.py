from __future__ import annotations

from namel3ss.parser.decl.page_story import parse_story_block


def parse_story_item(parser):
    return parse_story_block(parser)


__all__ = ["parse_story_item"]
