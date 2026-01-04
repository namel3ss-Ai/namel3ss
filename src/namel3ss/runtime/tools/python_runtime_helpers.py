from __future__ import annotations


def _tool_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


def _tool_pack_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    text is text\n\n"
        "  output:\n"
        "    text is text"
    )


def _binding_example(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "tools.my_tool:run"'
    )


__all__ = ["_binding_example", "_tool_example", "_tool_pack_example"]
