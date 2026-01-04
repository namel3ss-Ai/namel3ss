from __future__ import annotations

from namel3ss.cli.learning_support.render import render_expression
from namel3ss.ir import nodes as ir


def collect_requires(program: ir.Program) -> list[dict]:
    rules: list[dict] = []
    for flow in program.flows:
        if flow.requires:
            rules.append({"scope": "flow", "name": flow.name, "rule": render_expression(flow.requires)})
    for page in program.pages:
        if page.requires:
            rules.append({"scope": "page", "name": page.name, "rule": render_expression(page.requires)})
    return sorted(rules, key=lambda item: (item["scope"], item["name"]))


__all__ = ["collect_requires"]
