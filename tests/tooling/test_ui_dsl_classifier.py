from __future__ import annotations

from tools.spec_gates.ui_dsl_classifier import (
    classify_ui_dsl_semantic_files,
    is_ui_dsl_semantic_path,
    normalize_repo_path,
)


def test_is_ui_dsl_semantic_path_for_semantic_layers() -> None:
    assert is_ui_dsl_semantic_path("src/namel3ss/parser/decl/page_list.py")
    assert is_ui_dsl_semantic_path("src/namel3ss/ast/pages.py")
    assert is_ui_dsl_semantic_path("src/namel3ss/ir/lowering/pages_items/views.py")
    assert is_ui_dsl_semantic_path("src/namel3ss/ui/manifest/validation.py")
    assert is_ui_dsl_semantic_path("tools/generate_parser.py")


def test_is_ui_dsl_semantic_path_for_non_semantic_paths() -> None:
    assert not is_ui_dsl_semantic_path("docs/ui-dsl.md")
    assert not is_ui_dsl_semantic_path("tests/ui/test_manifest.py")
    assert not is_ui_dsl_semantic_path("src/namel3ss/studio/web/ui_renderer.js")


def test_classify_ui_dsl_semantic_files_is_sorted_and_deduped() -> None:
    paths = [
        "src\\namel3ss\\ui\\manifest\\elements\\views.py",
        "src/namel3ss/parser/decl/page_list.py",
        "src/namel3ss/parser/decl/page_list.py",
        "docs/ui-dsl.md",
    ]
    assert classify_ui_dsl_semantic_files(paths) == [
        "src/namel3ss/parser/decl/page_list.py",
        "src/namel3ss/ui/manifest/elements/views.py",
    ]


def test_normalize_repo_path_returns_empty_for_blank() -> None:
    assert normalize_repo_path("") == ""
    assert normalize_repo_path("   ") == ""
