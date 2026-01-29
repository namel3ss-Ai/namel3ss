from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import _parse_reference_name_value, _parse_string_value


def parse_ui_action_body(parser, *, entry_label: str, allow_pattern_params: bool = False) -> tuple[str, str | None, str | None]:
    tok = parser._current()
    if tok.type == "CALLS":
        parser._advance()
        parser._expect("FLOW", f"Expected 'flow' keyword in {entry_label.lower()}")
        flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
        return "call_flow", flow_name, None
    if tok.type == "IDENT" and tok.value in {"opens", "closes"}:
        op = tok.value
        parser._advance()
        target_tok = parser._current()
        if target_tok.type != "IDENT" or target_tok.value not in {"modal", "drawer"}:
            raise Namel3ssError(
                f"{entry_label} must open or close a modal or drawer",
                line=target_tok.line,
                column=target_tok.column,
            )
        parser._advance()
        label_tok = _parse_string_value(
            parser,
            allow_pattern_params=allow_pattern_params,
            context=f"{target_tok.value} label",
        )
        verb = "open" if op == "opens" else "close"
        kind = f"{verb}_{target_tok.value}"
        return kind, None, label_tok
    raise Namel3ssError(
        f"{entry_label} must call a flow or open/close a modal/drawer",
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_ui_action_body"]
