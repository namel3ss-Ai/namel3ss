from __future__ import annotations

from namel3ss.icons.registry import icon_names
from namel3ss.ui.external.serve import resolve_builtin_icon_file


def test_resolve_builtin_icon_file_returns_svg_asset() -> None:
    icon_name = icon_names()[0]
    file_path, content_type = resolve_builtin_icon_file(f"/icons/{icon_name}.svg")
    assert file_path is not None
    assert file_path.exists()
    assert file_path.suffix == ".svg"
    assert content_type == "image/svg+xml"


def test_resolve_builtin_icon_file_rejects_non_svg_suffix() -> None:
    icon_name = icon_names()[0]
    file_path, content_type = resolve_builtin_icon_file(f"/icons/{icon_name}.png")
    assert file_path is None
    assert content_type is None

