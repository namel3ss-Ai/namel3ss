from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.media import validate_media_role
from namel3ss.ir.model.pages import ImageItem


def lower_image_item(item: ast.ImageItem, *, attach_origin) -> ImageItem:
    alt = item.alt if item.alt is not None else ""
    role = validate_media_role(item.role, line=item.line, column=item.column)
    return attach_origin(ImageItem(src=item.src, alt=alt, role=role, line=item.line, column=item.column), item)


__all__ = ["lower_image_item"]
