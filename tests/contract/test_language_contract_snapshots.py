from __future__ import annotations

import inspect
import json
import sys
import types
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from namel3ss.errors import contract as error_contract
from namel3ss.errors.runtime import builder as runtime_builder
from namel3ss.ir.functions import model as functions_model
from namel3ss.ir.model import base as ir_base
from namel3ss.ir.model import (
    agents,
    ai,
    contracts,
    expressions,
    flow_steps,
    jobs,
    pages,
    policy,
    program,
    statements,
    tools,
)
from namel3ss.lang.keywords import reserved_keywords
from namel3ss.parser.grammar_table import expression_rules, statement_rules, top_level_rules

ROOT = Path(__file__).resolve().parents[2]


def _read_contract_block(path: Path, name: str) -> dict:
    text = path.read_text(encoding="utf-8")
    start = f"<!-- CONTRACT:{name} -->"
    end = f"<!-- END_CONTRACT:{name} -->"
    if start not in text:
        raise AssertionError(f"Missing contract block {name} in {path}")
    segment = text.split(start, 1)[1]
    if end not in segment:
        raise AssertionError(f"Missing end marker for {name} in {path}")
    segment = segment.split(end, 1)[0]
    fence_start = segment.find("```json")
    if fence_start == -1:
        raise AssertionError(f"Missing json fence in {path} for {name}")
    fenced = segment[fence_start + len("```json") :]
    fence_end = fenced.find("```")
    if fence_end == -1:
        raise AssertionError(f"Unclosed json fence in {path} for {name}")
    payload = fenced[:fence_end].strip()
    return json.loads(payload)


def _grammar_snapshot() -> dict:
    return {
        "reserved_keywords": list(reserved_keywords()),
        "top_level_rules": [rule.name for rule in top_level_rules()],
        "statement_rules": [rule.name for rule in statement_rules()],
        "expression_rules": [rule.name for rule in expression_rules()],
    }


def _type_hints(cls) -> dict:
    module = sys.modules.get(cls.__module__)
    try:
        return get_type_hints(
            cls,
            globalns=vars(module) if module else None,
            localns=vars(module) if module else None,
        )
    except Exception:
        return {}


def _is_optional(tp) -> bool:
    origin = get_origin(tp)
    if origin is None:
        return False
    if origin is types.UnionType:
        return types.NoneType in get_args(tp)
    if origin is getattr(__import__("typing"), "Union", None):
        return types.NoneType in get_args(tp)
    return False


def _ir_schema_snapshot() -> dict:
    modules = [
        ir_base,
        program,
        contracts,
        policy,
        jobs,
        flow_steps,
        statements,
        expressions,
        ai,
        agents,
        pages,
        tools,
        functions_model,
    ]
    nodes: dict[str, list[str]] = {}
    for module in modules:
        for _name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            if not is_dataclass(cls):
                continue
            if not issubclass(cls, ir_base.Node):
                continue
            hints = _type_hints(cls)
            field_list: list[str] = []
            for field in fields(cls):
                tp = hints.get(field.name, field.type)
                if isinstance(tp, str):
                    optional = "None" in tp or "Optional" in tp
                else:
                    optional = _is_optional(tp)
                label = f"{field.name}?" if optional else field.name
                field_list.append(label)
            nodes[cls.__name__] = field_list

    alias_args = get_args(expressions.Assignable)
    alias = " | ".join(cls.__name__ for cls in alias_args)
    return {
        "aliases": {"Assignable": alias},
        "nodes": {name: nodes[name] for name in sorted(nodes)},
    }


def _error_conventions_snapshot() -> dict:
    templates = json.loads(json.dumps(runtime_builder._TEMPLATES))
    return {
        "categories": list(error_contract.ERROR_CATEGORIES),
        "kind_category_map": dict(error_contract._KIND_CATEGORY_MAP),
        "default_codes": dict(error_contract._DEFAULT_CODES),
        "fallback_messages": dict(error_contract._FALLBACK_MESSAGES),
        "runtime_templates": templates,
    }


def test_grammar_contract_snapshot_matches_code() -> None:
    doc = ROOT / "docs" / "language" / "grammar_contract.md"
    expected = _read_contract_block(doc, "grammar")
    assert expected == _grammar_snapshot()


def test_ir_schema_snapshot_matches_code() -> None:
    doc = ROOT / "docs" / "language" / "ir_schema.md"
    expected = _read_contract_block(doc, "ir_schema")
    assert expected == _ir_schema_snapshot()


def test_error_conventions_snapshot_matches_code() -> None:
    doc = ROOT / "docs" / "language" / "error_conventions.md"
    expected = _read_contract_block(doc, "error_conventions")
    assert expected == _error_conventions_snapshot()
