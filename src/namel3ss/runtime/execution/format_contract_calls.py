from __future__ import annotations

import json

from namel3ss.ir import nodes as ir


def format_contract_call(
    *,
    kind: str,
    name: str,
    arguments: list[ir.CallArg],
    outputs: list[str],
    formatter,
) -> str:
    name_text = json.dumps(name, ensure_ascii=True)
    lines = [f"call {kind} {name_text}:", "  input:"]
    for arg in arguments:
        line = f"{arg.name} is {formatter(arg.value)}"
        lines.extend(_indent_block(line, indent="    "))
    lines.append("  output:")
    for output_name in outputs:
        lines.extend(_indent_block(output_name, indent="    "))
    return "\n".join(lines)


def _indent_block(text: str, indent: str = "  ") -> list[str]:
    lines = text.splitlines() if text else [""]
    return [f"{indent}{line}" for line in lines]


__all__ = ["format_contract_call"]
