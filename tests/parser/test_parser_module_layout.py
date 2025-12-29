from __future__ import annotations

import importlib
from pathlib import Path


def test_parser_module_layout() -> None:
    base = Path(__file__).resolve().parents[2] / "src" / "namel3ss" / "parser"
    required_dirs = ("core", "decl", "stmt", "expr")
    required_files = (
        "grammar_table.py",
        "parse_program.py",
        "core/tokens.py",
        "core/stream.py",
        "core/errors.py",
        "core/helpers.py",
        "decl/record.py",
        "decl/flow.py",
        "decl/page.py",
        "decl/ai.py",
        "decl/agent.py",
        "decl/tool.py",
        "decl/use.py",
        "decl/capsule.py",
        "stmt/common.py",
        "stmt/let.py",
        "expr/ops.py",
        "expr/refs.py",
    )
    for name in required_dirs:
        assert (base / name).is_dir(), f"Missing parser folder {name}"
    for path in required_files:
        assert (base / path).is_file(), f"Missing parser file {path}"
    for module in (
        "namel3ss.parser.core",
        "namel3ss.parser.grammar_table",
        "namel3ss.parser.parse_program",
        "namel3ss.parser.decl.record",
        "namel3ss.parser.decl.flow",
        "namel3ss.parser.stmt.common",
        "namel3ss.parser.expr.ops",
    ):
        importlib.import_module(module)
