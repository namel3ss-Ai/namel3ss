from __future__ import annotations

from namel3ss.parser.incremental import IncrementalEdit, full_parse_state, incremental_parse
from tests.spec_freeze.helpers.ast_dump import dump_ast


def _dump_tokens(tokens):
    return [
        {
            "type": tok.type,
            "value": tok.value,
            "line": tok.line,
            "column": tok.column,
            "escaped": tok.escaped,
        }
        for tok in tokens
        if tok.type != "EOF"
    ]


def _dump_state(state):
    return {
        "tokens": _dump_tokens(state.tokens),
        "ast": dump_ast(state.program) if state.program else None,
        "error": state.error,
    }


def _apply_edit_text(source: str, edit: IncrementalEdit) -> str:
    return source[: edit.start] + edit.insert_text + source[edit.start + edit.delete_len :]


def _build_edits(source: str, ops: list[dict]) -> list[IncrementalEdit]:
    edits: list[IncrementalEdit] = []
    working = source
    for op in ops:
        kind = op["kind"]
        if kind == "insert_before":
            start = working.index(op["marker"])
            edit = IncrementalEdit(start=start, delete_len=0, insert_text=op["text"])
        elif kind == "replace":
            start = working.index(op["old"])
            edit = IncrementalEdit(start=start, delete_len=len(op["old"]), insert_text=op["new"])
        elif kind == "delete":
            start = working.index(op["old"])
            edit = IncrementalEdit(start=start, delete_len=len(op["old"]), insert_text="")
        else:
            raise ValueError(f"Unknown edit kind: {kind}")
        edits.append(edit)
        working = _apply_edit_text(working, edit)
    return edits


def _run_incremental(source: str, edits: list[IncrementalEdit]):
    state = full_parse_state(source)
    for edit in edits:
        state = incremental_parse(state, edit)
    return state


def test_incremental_parse_matches_full_parse() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        '  let total is 1\n'
        '  return total\n'
    )
    scenarios = [
        (
            "insert_line",
            source,
            _build_edits(
                source,
                [
                    {
                        "kind": "insert_before",
                        "marker": "  return total",
                        "text": "  let extra is 2\n",
                    }
                ],
            ),
        ),
        (
            "replace_literal",
            source,
            _build_edits(
                source,
                [
                    {
                        "kind": "replace",
                        "old": "1",
                        "new": "2",
                    }
                ],
            ),
        ),
        (
            "remove_colon",
            source,
            _build_edits(
                source,
                [
                    {
                        "kind": "delete",
                        "old": ":",
                    }
                ],
            ),
        ),
        (
            "multi_step",
            source,
            _build_edits(
                source,
                [
                    {
                        "kind": "insert_before",
                        "marker": "  return total",
                        "text": "  let extra is 2\n",
                    },
                    {
                        "kind": "replace",
                        "old": "return total",
                        "new": "return extra",
                    },
                ],
            ),
        ),
    ]
    for _, base, edits in scenarios:
        incremental_state = _run_incremental(base, edits)
        full_state = full_parse_state(_apply_edits(base, edits))
        assert _dump_state(incremental_state) == _dump_state(full_state)
        repeat_state = _run_incremental(base, edits)
        assert _dump_state(repeat_state) == _dump_state(incremental_state)


def _apply_edits(source: str, edits: list[IncrementalEdit]) -> str:
    working = source
    for edit in edits:
        working = _apply_edit_text(working, edit)
    return working
